"""Real HTTPS transport conformance using disposable keys and a recording application."""
import concurrent.futures
import http.client
import ipaddress
import socket
import ssl
import tempfile
import threading
import unittest
from contextlib import closing, contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from .common import MAX_BYTES, VERSION, Error, strict_json
from .transport import CandidateClient, serve


def make_test_certificate(directory, name='fixture', ip='127.0.0.1'):
    """Temporary self-signed server cert. Never installed in an OS trust store."""
    key = ec.generate_private_key(ec.SECP256R1())
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)])
    now = datetime.now(timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(subject).issuer_name(subject)
            .public_key(key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(minutes=2)).not_valid_after(now + timedelta(hours=1))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address(ip))]), critical=False)
            .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
            .sign(key, hashes.SHA256()))
    cert_path, key_path = directory / (name + '.pem'), directory / (name + '.key')
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                           serialization.NoEncryption()))
    return cert_path, key_path


class RecordingFactory:
    def __init__(self):
        self.calls = []
        self.instances = []
        self.rows = [{'id': 1, 'event': 'queued', 'data': {'note': 'synthetic\nline'}},
                     {'id': 2, 'event': 'claimed', 'data': {'project': 'pA'}}]
        self.release_failure = None
        self.release_barrier = 1
        self.dispatch_fault = None
        self.entered = threading.Event()
        self.proceed = threading.Event()
        self.pause = False
        self.has_release_guard = True

    def __call__(self):
        application = RecordingApplication(self)
        if not self.has_release_guard:
            application.release_unit = None
        self.instances.append(application)
        return application


class RecordingApplication:
    def __init__(self, factory):
        self.factory = factory
        self.closed = threading.Event()
        self.releases = []

    def dispatch(self, operation, token, body):
        self.factory.calls.append((operation, token, body))
        if self.factory.pause:
            self.factory.entered.set()
            if not self.factory.proceed.wait(3):
                raise RuntimeError('fixture timeout')
        if self.factory.dispatch_fault:
            raise self.factory.dispatch_fault
        if operation == 'events':
            return {'events': [row for row in self.factory.rows if row['id'] > body['after']]}
        if operation in {'run_start', 'run_cancel', 'worker_admit'}:
            return {'accepted': True, 'state': 'queued', 'stateVersion': 1, 'runId': 'runA'}
        return {'received': body}

    @contextmanager
    def release_unit(self, operation, token, body, result):
        self.releases.append((operation, token, body, result))
        if self.factory.release_failure and len(self.releases) == self.factory.release_barrier:
            raise self.factory.release_failure
        yield

    def close(self):
        self.closed.set()


class TransportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(directory.cleanup)
        cls.cert, cls.key = make_test_certificate(Path(directory.name))
        cls.other, _ = make_test_certificate(Path(directory.name), 'other')
        cls.wrong_host, cls.wrong_host_key = make_test_certificate(Path(directory.name), 'otherip', '127.0.0.2')

    def setUp(self):
        self.factory = RecordingFactory()
        self.server = self.start_server(self.cert, self.key)
        self.host, self.port = self.server.server_address
        self.client = CandidateClient(self.host, self.port, self.cert)

    def start_server(self, certificate, key):
        server = serve(self.factory, certificate, key)
        thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': 0.01})
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(thread.join)
        self.addCleanup(server.shutdown)
        return server

    def message(self, path, headers, body=b'', method='POST'):
        head = f'{method} {path} HTTP/1.1\r\nHost: {self.server.authority}\r\n' + headers + '\r\n'
        return head.encode('ascii') + body

    def exchange(self, request):
        with socket.create_connection((self.host, self.port), timeout=3) as plain:
            with self.client.tls.wrap_socket(plain, server_hostname=self.host) as secure:
                secure.sendall(request)
                with closing(http.client.HTTPResponse(secure)) as response:
                    response.begin()
                    return response.status, response.getheader('Content-Type'), response.read()

    def test_independent_verified_clients_and_per_request_close(self):
        second = CandidateClient(self.host, self.port, self.cert)
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            first = pool.submit(self.client.call, 'session_login', None, {'sample': 'synthetic'})
            other = pool.submit(second.call, 'run_read', 't.two', {'project': 'pB'})
            self.assertEqual({'received': {'sample': 'synthetic'}}, first.result())
            self.assertEqual({'received': {'project': 'pB'}}, other.result())
        self.assertCountEqual([('session_login', None, {'sample': 'synthetic'}),
                               ('run_read', 't.two', {'project': 'pB'})], self.factory.calls)
        self.assertEqual(2, len(self.factory.instances))
        self.assertTrue(all(app.closed.wait(1) for app in self.factory.instances))
        self.assertEqual(2, sum(len(app.releases) for app in self.factory.instances))

    def test_certificate_and_hostname_verified_before_dispatch(self):
        with self.assertRaises(ssl.SSLCertVerificationError):
            CandidateClient(self.host, self.port, self.other).call('session_login', None, {})
        server = self.start_server(self.wrong_host, self.wrong_host_key)
        with self.assertRaises(ssl.SSLCertVerificationError):
            CandidateClient(*server.server_address, self.wrong_host).call('session_login', None, {})
        self.assertFalse(self.factory.instances)

    def test_loopback_literal_only(self):
        for host in ('0.0.0.0', '::', 'localhost', '192.0.2.1'):
            with self.subTest(host=host), self.assertRaises(Error):
                serve(self.factory, self.cert, self.key, host=host)

    def test_bad_requests_precede_application_creation(self):
        path = '/v1/run_read'
        h = 'Content-Type: application/json\r\nAuthorization: Bearer t.one\r\n'
        valid = h + 'Content-Length: 2\r\n'
        samples = [
            (path, h, b'', 'POST', 'E_INPUT'),
            (path, h + f'Content-Length: {MAX_BYTES + 1}\r\n', b'', 'POST', 'E_SIZE'),
            (path, valid + 'content-length: 2\r\n', b'{}', 'POST', 'E_INPUT'),
            (path, valid + 'Authorization: Bearer t.two\r\n', b'{}', 'POST', 'E_INPUT'),
            (path, valid + 'Transfer-Encoding: chunked\r\n', b'{}', 'POST', 'E_INPUT'),
            (path, valid + 'Origin: null\r\n', b'{}', 'POST', 'E_INPUT'),
            (path, valid + 'Cookie: x=y\r\n', b'{}', 'POST', 'E_INPUT'),
            (path, valid.replace('Bearer t.one', 'Basic t.one'), b'{}', 'POST', 'E_AUTH'),
            (path, valid.replace('Authorization: Bearer t.one\r\n', ''), b'{}', 'POST', 'E_AUTH'),
            (path, valid.replace('application/json', 'text/plain'), b'{}', 'POST', 'E_MEDIA'),
            (path + '?id=x', valid, b'{}', 'POST', 'E_ROUTE'),
            ('/v1/release_check', valid, b'{}', 'POST', 'E_ROUTE'),
            (path, valid, b'{}', 'PUT', 'E_METHOD'),
            ('/v1/events?project=pA&after=0', '', b'', 'GET', 'E_INPUT'),
            ('/v1/events?project=pA&run=runA&run=runB&after=0', '', b'', 'GET', 'E_INPUT'),
            ('/v1/events?project=pA&run=runA&after=0', 'Last-Event-ID: 1\r\n', b'', 'GET', 'E_INPUT'),
            ('/v1/events?project=pA&run=runA&after=0', 'Content-Length: 1\r\n', b'x', 'GET', 'E_INPUT'),
        ]
        for body in (b'{"x":1,"x":2}', b'{"x":1e999}', b'{"x":NaN}', b'\xff', b'[]', b'{}1'):
            samples.append((path, h + f'Content-Length: {len(body)}\r\n', body, 'POST', 'E_INPUT'))
        for target, headers, body, method, code in samples:
            with self.subTest(target=target, headers=headers, body=body, method=method):
                status, media, raw = self.exchange(self.message(target, headers, body, method))
                self.assertGreaterEqual(status, 400)
                self.assertEqual('application/json', media)
                self.assertEqual({'error': code}, strict_json(raw))
        self.assertFalse(self.factory.instances)

    def test_event_wire_encoding_reconnect_and_empty_page(self):
        query = '/v1/events?project=pA&run=runA'
        auth = 'Authorization: Bearer t.one\r\n'
        status, media, raw = self.exchange(self.message(query, auth + 'Last-Event-ID: 1\r\n', method='GET'))
        self.assertEqual((200, 'text/event-stream; charset=utf-8', b'id: 2\nevent: claimed\ndata: {"project":"pA"}\n\n'),
                         (status, media, raw))
        self.assertEqual(self.factory.rows, self.client.events('pA', 'runA', 't.one'))
        self.assertEqual([], self.client.events('pA', 'runA', 't.one', 2))
        self.assertEqual(('events', 't.one', {'version': VERSION, 'project': 'pA', 'run_id': 'runA', 'after': 2}), self.factory.calls[-1])

    def test_unknown_post_with_split_header_body_gets_complete_error(self):
        # http.client sends request headers and a nonempty body in distinct TLS writes.
        # A route error must consume bounded framing before closing, not discard its reply.
        with closing(http.client.HTTPSConnection(self.host, self.port, context=self.client.tls, timeout=10)) as connection:
            body = b'{"padding":"' + b'x' * 12000 + b'"}'
            connection.request('POST', '/v1/attachment', body=body,
                               headers={'Content-Type': 'application/json', 'Authorization': 'Bearer t.one'})
            with closing(connection.getresponse()) as response:
                self.assertEqual(response.status, 404)
                self.assertEqual(strict_json(response.read()), {'error': 'E_ROUTE'})
        self.assertFalse(self.factory.instances)

    def test_invalid_event_batch_releases_no_data(self):
        for row, code in [({'id': 2, 'event': 'queued', 'data': {}}, 'E_RESYNC_REQUIRED'),
                          ({'id': 1, 'event': 'bad\nevent', 'data': {}}, 'E_INTERNAL'),
                          ({'id': 1, 'event': 'queued', 'data': {'s': 'x' * MAX_BYTES}}, 'E_INTERNAL')]:
            self.factory.rows = [row]
            with self.subTest(code=code), self.assertRaisesRegex(Error, code):
                self.client.events('pA', 'runA', 't.one')

    def test_denial_immediately_before_json_and_event_release(self):
        self.factory.release_failure = Error('E_DENIED')
        for operation in ('events', 'run_read', 'report_read', 'source_read', 'report_export'):
            with self.subTest(operation=operation), self.assertRaisesRegex(Error, 'E_DENIED'):
                if operation == 'events':
                    self.client.events('pA', 'runA', 't.one')
                else:
                    self.client.call(operation, 't.one', {})
        self.assertEqual(5, len(self.factory.calls))
        self.assertTrue(all(len(app.releases) == 1 and app.closed.wait(1) for app in self.factory.instances))

    def test_missing_release_dependency_fails_closed(self):
        self.factory.has_release_guard = False
        with self.assertRaisesRegex(Error, 'E_DEPENDENCY'):
            self.client.call('report_export', 't.one', {})
        self.assertTrue(self.factory.instances[0].closed.wait(1))

    def test_revocation_between_chunks_and_events_truncates_connection(self):
        self.factory.release_failure = Error('E_DENIED')
        self.factory.release_barrier = 3
        body = b'{"note":"' + b'x' * 7000 + b'"}'
        auth = 'Authorization: Bearer t.one\r\n'
        requests = [
            (self.message('/v1/report_read', auth + f'Content-Length: {len(body)}\r\n'
                          'Content-Type: application/json\r\n', body), 4096),
            (self.message('/v1/events?project=pA&run=runA&after=0', auth, method='GET'),
             len(b'id: 1\nevent: queued\ndata: {"note":"synthetic\\nline"}\n\n'))
        ]
        for request, expected_bytes in requests:
            with self.subTest(expected_bytes=expected_bytes), self.assertRaises(http.client.IncompleteRead) as err:
                self.exchange(request)
            self.assertEqual(expected_bytes, len(err.exception.partial))
            self.assertNotIn(b'E_DENIED', err.exception.partial)
        self.assertTrue(all(app.closed.wait(1) for app in self.factory.instances))

    def test_http_accepted_and_ordinary_response_size(self):
        result = self.client.call('run_start', 't.one', {})
        self.assertIs(result['accepted'], True)
        body = {'note': 'x' * (64 * 1024)}
        with self.assertRaisesRegex(Error, 'E_INTERNAL'):
            self.client.call('report_read', 't.one', body)
        self.assertEqual({'received': body}, self.client.call('session_login', None, body))

    def test_internal_exception_and_unrecognized_error_redaction(self):
        for fault in (RuntimeError('fixture_private'), Error('fixture_private'), Error('E_ROUTE'), Error('E_NOT_FOUND')):
            self.factory.dispatch_fault = fault
            with self.assertRaisesRegex(Error, '^E_INTERNAL$'):
                self.client.call('run_start', 't.one', {})
        self.assertTrue(all(app.closed.wait(1) for app in self.factory.instances))

    def test_peer_disconnect_closes_once_without_redispatch(self):
        self.factory.pause = True
        request = self.message('/v1/run_start', 'Authorization: Bearer t.one\r\nContent-Length: 2\r\n'
                               'Content-Type: application/json\r\n', b'{}')
        try:
            with socket.create_connection((self.host, self.port), timeout=3) as raw:
                with self.client.tls.wrap_socket(raw, server_hostname=self.host) as peer:
                    peer.sendall(request)
                    self.assertTrue(self.factory.entered.wait(2))
        finally:
            self.factory.proceed.set()
        self.assertTrue(self.factory.instances[0].closed.wait(2))
        self.assertEqual([('run_start', 't.one', {})], self.factory.calls)


if __name__ == '__main__':
    unittest.main()
