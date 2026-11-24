"""One-request HTTPS transport for the loopback synthetic application candidate."""
import http.client
import ipaddress
import re
import socket
import socketserver
import ssl
from contextlib import closing, contextmanager, nullcontext
from http import HTTPStatus

from .common import MAX_BYTES, OPERATIONS, PUBLIC_OPERATIONS, VERSION, Error, canonical, identifier, require, strict_json


APPLICATION_STATUS = {
    'E_INPUT': 400, 'E_VERSION': 426, 'E_AUTH': 401, 'E_DENIED': 403,
    'E_CONFLICT': 409, 'E_STALE': 409, 'E_BUDGET': 429, 'E_UNRESOLVED': 409,
    'E_RESYNC_REQUIRED': 409, 'E_INTEGRITY': 409, 'E_DEPENDENCY': 503,
}
STATUS = {**APPLICATION_STATUS, 'E_ROUTE': 404, 'E_METHOD': 405, 'E_SIZE': 413,
          'E_MEDIA': 415, 'E_INTERNAL': 500}
MAX_CURSOR = (1 << 63) - 1
MAX_EVENTS = 64
ORDINARY_LIMIT = 64 * 1024
CHUNK_SIZE = 4096
PROTECTED_READS = frozenset(('session_read', 'project_list', 'project_read', 'run_list', 'run_read',
                             'events', 'report_read', 'source_read', 'report_export'))
ACCEPTED_COMMANDS = frozenset(('run_start', 'run_cancel', 'worker_admit'))
BEARER = re.compile(r'Bearer ([A-Za-z0-9._~+/-]{1,4096}={0,2})', re.ASCII)
EVENT = re.compile(r'[A-Za-z][A-Za-z0-9_.-]{0,63}', re.ASCII)
HEADER = re.compile(rb"([!#$%&'*+.^_`|~A-Za-z0-9-]+):([ -~\t]*)\r\n")
JSON_TYPE = 'application/json'
SSE_TYPE = 'text/event-stream; charset=utf-8'


def _address(host):
    require(isinstance(host, str))
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        raise Error('E_INPUT') from None
    require(address.is_loopback and '%' not in host)
    return address


def _headers(reader):
    headers = {}
    total = 0
    while True:
        line = reader.readline(8193)
        total += len(line)
        require(len(line) <= 8192 and total <= 32768)
        if line == b'\r\n':
            return headers
        match = HEADER.fullmatch(line)
        require(match and len(headers) < 64)
        name = match[1].lower().decode('ascii')
        require(name not in headers)
        headers[name] = match[2].strip(b' \t').decode('ascii')


def _cursor(value):
    require(re.fullmatch(r'0|[1-9][0-9]{0,18}', value))
    result = int(value)
    require(result <= MAX_CURSOR)
    return result


def _event_request(target, headers):
    require('content-type' not in headers and headers.get('content-length', '0') == '0')
    path, separator, query = target.partition('?')
    require(path == '/v1/events', 'E_ROUTE')
    require(separator)
    fields = {}
    for part in query.split('&'):
        key, sep, value = part.partition('=')
        require(sep and key in {'project', 'run', 'after'} and key not in fields)
        fields[key] = value
    require({'project', 'run'} <= fields.keys())
    project = identifier(fields['project'])
    # A reconnect can send the last delivered ID. Conflicting cursors are ambiguous.
    last_id = headers.get('last-event-id')
    require('after' in fields or last_id is not None)
    after = _cursor(fields['after'] if 'after' in fields else last_id)
    require(last_id is None or _cursor(last_id) == after)
    return {'version': VERSION, 'project': project, 'run_id': identifier(fields['run']), 'after': after}


def _token(operation, headers):
    authorization = headers.get('authorization')
    if authorization is None:
        require(operation in PUBLIC_OPERATIONS, 'E_AUTH')
        return None
    match = BEARER.fullmatch(authorization)
    require(match, 'E_AUTH')
    return match[1]


def _sse(result, after):
    require(isinstance(result, dict) and set(result) == {'events'}, 'E_INTERNAL')
    rows = result['events']
    require(isinstance(rows, list) and len(rows) <= MAX_EVENTS, 'E_INTERNAL')
    parts = []
    length = 0
    for row in rows:
        require(isinstance(row, dict) and set(row) == {'id', 'event', 'data'}, 'E_INTERNAL')
        sequence, event, data = row['id'], row['event'], row['data']
        require(type(sequence) is int and 0 < sequence <= MAX_CURSOR, 'E_INTERNAL')
        require(sequence == after + 1, 'E_RESYNC_REQUIRED')
        require(isinstance(event, str) and EVENT.fullmatch(event) and isinstance(data, dict), 'E_INTERNAL')
        record = f'id: {sequence}\nevent: {event}\ndata: '.encode('ascii') + canonical(data) + b'\n\n'
        length += len(record)
        require(length <= ORDINARY_LIMIT, 'E_INTERNAL')
        parts.append(record)
        after = sequence
    return parts


@contextmanager
def _application_boundary():
    try:
        yield
    except Error as exc:
        if isinstance(exc.code, str) and exc.code in APPLICATION_STATUS:
            raise
        raise Error('E_INTERNAL') from None


class _Request(socketserver.StreamRequestHandler):
    timeout = 10

    def setup(self):
        self.request.settimeout(self.timeout)
        self.request = self.server.tls.wrap_socket(self.request, server_side=True)
        try:
            super().setup()
        except BaseException:
            self.request.close()
            raise

    def finish(self):
        try:
            super().finish()
        finally:
            self.request.close()

    def handle(self):
        self.response_started = False
        try:
            self.process()
            return
        except Error as exc:
            code = exc.code if isinstance(exc.code, str) and exc.code in STATUS else 'E_INTERNAL'
            status, media, body = STATUS[code], JSON_TYPE, canonical({'error': code})
        except Exception:
            status, media, body = 500, JSON_TYPE, b'{"error":"E_INTERNAL"}'
        if not self.response_started:
            self.send(status, media, [body])

    def send(self, status, media, parts, release_unit=nullcontext):
        length = sum(map(len, parts))
        head = (f'HTTP/1.1 {status} {HTTPStatus(status).phrase}\r\nContent-Type: {media}\r\n'
                f'Content-Length: {length}\r\nCache-Control: no-store\r\n'
                'X-Content-Type-Options: nosniff\r\nConnection: close\r\n\r\n').encode('ascii')
        with release_unit():
            self.response_started = True
            self.wfile.write(head)
        for part in parts:
            for offset in range(0, len(part), CHUNK_SIZE):
                chunk = part[offset:offset + CHUNK_SIZE]
                with release_unit():
                    self.wfile.write(chunk)

    def process(self):
        line = self.rfile.readline(4097)
        match = re.fullmatch(rb'([A-Z]+) ([!-~]+) HTTP/1\.1\r\n', line)
        require(len(line) <= 4096 and match)
        method, target = (value.decode('ascii') for value in match.groups())
        headers = _headers(self.rfile)
        require(headers.get('host') == self.server.authority)
        require(not headers.keys() & {'transfer-encoding', 'content-encoding', 'expect', 'trailer',
                                       'cookie', 'origin', 'upgrade', 'proxy-authorization'})
        require(method in {'POST', 'GET'}, 'E_METHOD')
        if method == 'POST':
            # Read the bounded, explicitly framed body before rejecting route/auth.
            # HTTPS clients commonly send headers/body as separate TLS records; closing
            # with a legitimate body unread can reset the connection and discard 404 JSON.
            length = headers.get('content-length', '')
            require(re.fullmatch(r'0|[1-9][0-9]{0,18}', length))
            require(int(length) <= MAX_BYTES, 'E_SIZE')
            raw = self.rfile.read(int(length))
            require(len(raw) == int(length))
            require(target.startswith('/v1/'), 'E_ROUTE')
            operation = target[4:]
            require(operation in OPERATIONS, 'E_ROUTE')
            token = _token(operation, headers)
            require('last-event-id' not in headers)
            require(headers.get('content-type', '').lower() in {JSON_TYPE, JSON_TYPE + '; charset=utf-8'}, 'E_MEDIA')
            body = strict_json(raw)
            require(isinstance(body, dict))
        else:
            operation = 'events'
            body = _event_request(target, headers)
            token = _token(operation, headers)
        with _application_boundary(), closing(self.server.application_factory()) as app:
            result = app.dispatch(operation, token, body)
            require(isinstance(result, dict), 'E_INTERNAL')
            protected = operation in PROTECTED_READS
            if method == 'GET':
                media, parts = SSE_TYPE, _sse(result, body['after'])
            else:
                media, parts = JSON_TYPE, [canonical(result)]
                limit = ORDINARY_LIMIT if protected else MAX_BYTES
                require(len(parts[0]) <= limit, 'E_INTERNAL')
            status = 200
            if operation in ACCEPTED_COMMANDS:
                require(result.get('accepted') is True, 'E_INTERNAL')
                status = 202
            if protected:
                guard = getattr(app, 'release_unit', None)
                require(callable(guard), 'E_DEPENDENCY')
                def release_unit():
                    return guard(operation, token, body, result)
                self.send(status, media, parts, release_unit)
            else:
                self.send(status, media, parts)


class _Server(socketserver.ThreadingTCPServer):
    def handle_error(self, request, client_address):
        # Handshake failures and disconnected peers never write request details to stderr.
        pass


class _IPv6Server(_Server):
    address_family = socket.AF_INET6


def serve(application_factory, certificate_path, key_path, *, host='127.0.0.1', port=0):
    address = _address(host)
    tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls.minimum_version = ssl.TLSVersion.TLSv1_2
    tls.load_cert_chain(certificate_path, key_path)
    server_type = _Server if address.version == 4 else _IPv6Server
    server = server_type((str(address), port), _Request)
    server.application_factory = application_factory
    server.tls = tls
    hostname = str(address) if address.version == 4 else f'[{address}]'
    server.authority = f'{hostname}:{server.server_address[1]}'
    return server


class CandidateClient:
    """Open a fresh verified connection per call. No automatic application retries."""
    def __init__(self, host, port, certificate_path, *, timeout=10):
        self.host = str(_address(host))
        self.port = port
        self.timeout = timeout
        self.tls = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        self.tls.minimum_version = ssl.TLSVersion.TLSv1_2
        self.tls.load_verify_locations(cafile=certificate_path)

    def _request(self, method, target, token, body, media, expected_status=200):
        authority_host = f'[{self.host}]' if ':' in self.host else self.host
        headers = {'Host': f'{authority_host}:{self.port}'}
        if token is not None:
            require(isinstance(token, str) and BEARER.fullmatch('Bearer ' + token), 'E_AUTH')
            headers['Authorization'] = 'Bearer ' + token
        if body is not None:
            headers['Content-Type'] = JSON_TYPE
        connection = http.client.HTTPSConnection(self.host, self.port, context=self.tls, timeout=self.timeout)
        with closing(connection):
            connection.request(method, target, body, headers)
            response = connection.getresponse()
            raw = response.read(MAX_BYTES + 1)
            require(len(raw) <= MAX_BYTES and response.getheader('Content-Length') == str(len(raw)), 'E_INTERNAL')
            response_type = response.getheader('Content-Type')
            if response.status != expected_status:
                require(response_type == JSON_TYPE, 'E_INTERNAL')
                error = strict_json(raw)
                require(isinstance(error, dict), 'E_INTERNAL')
                code = error.get('error')
                require(isinstance(code, str) and STATUS.get(code) == response.status, 'E_INTERNAL')
                raise Error(code)
            require(response_type == media, 'E_INTERNAL')
            return raw

    def call(self, operation, token, body):
        require(operation in OPERATIONS and isinstance(body, dict))
        raw = canonical(body)
        require(len(raw) <= MAX_BYTES, 'E_SIZE')
        status = 202 if operation in ACCEPTED_COMMANDS else 200
        result = strict_json(self._request('POST', '/v1/' + operation, token, raw, JSON_TYPE, status))
        require(isinstance(result, dict), 'E_INTERNAL')
        return result

    def events(self, project, run_id, token, after=0):
        identifier(project)
        identifier(run_id)
        require(type(after) is int and 0 <= after <= MAX_CURSOR)
        raw = self._request('GET', f'/v1/events?project={project}&run={run_id}&after={after}', token, None, SSE_TYPE)
        if not raw:
            return []
        require(raw.endswith(b'\n\n'), 'E_INTERNAL')
        rows = []
        for record in raw[:-2].split(b'\n\n'):
            match = re.fullmatch(rb'id: ([0-9]{1,19})\nevent: ([A-Za-z][A-Za-z0-9_.-]{0,63})\ndata: ([^\r\n]*)', record)
            require(match and len(rows) < MAX_EVENTS, 'E_INTERNAL')
            sequence = _cursor(match[1].decode('ascii'))
            data = strict_json(match[3])
            require(sequence == after + 1, 'E_RESYNC_REQUIRED')
            require(isinstance(data, dict), 'E_INTERNAL')
            rows.append({'id': sequence, 'event': match[2].decode('ascii'), 'data': data})
            after = sequence
        return rows
