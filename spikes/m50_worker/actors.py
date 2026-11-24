"""Spawned loopback TLS actors. Credentials and lease tokens travel only over private pipes."""
from contextlib import closing, contextmanager
import multiprocessing
import os
import time

from runtime_candidate.common import Error, VERSION, require
from runtime_candidate.transport import CandidateClient


def request(client, op, token=None, **body):
    return client.call(op, token, dict(body, version=VERSION))


def ui_process(pipe):
    with closing(pipe):
        endpoint, token, body = pipe.recv()
        started = request(CandidateClient(*endpoint), 'run_start', token, **body)
        pipe.send(('started', {'pid': os.getpid(), 'result': started}))
        require(pipe.poll(50) and pipe.recv() == ('exit', None), 'E_CHANNEL')


def _attempt(client, op, token, body):
    try:
        return {'result': request(client, op, token, **body)}
    except Error as exc:
        return {'denied': exc.code}


def driver_process(pipe):
    with closing(pipe):
        endpoint, scope, scheduler, worker = pipe.recv()
        client = CandidateClient(*endpoint)
        assignment = request(client, 'worker_claim', scheduler, **scope, worker='worker', expected_run_version=1)
        body = dict(scope, **{key: assignment[key] for key in ('assignment', 'fence', 'lease_token')})
        admission = request(client, 'worker_admit', worker, **body)
        pipe.send(('admitted', {'pid': os.getpid(), 'body': body, 'admission': admission}))
        monitor = True
        polls = 0
        deadline = time.monotonic() + 150
        while time.monotonic() < deadline:
            if pipe.poll(.15):
                op, payload = pipe.recv()
                if op == 'exit':
                    return
                if op == 'probe_collector_audience':
                    pipe.send(('worker_response', _attempt(client, 'collector_record', worker, payload)))
                elif op == 'launch_lost':
                    monitor = False
                    pipe.send(('whole_unit_signal', {'pid': os.getpid(), 'positivePolls': polls}))
                elif op == 'renew':
                    pipe.send(('worker_response', _attempt(client, 'worker_renew', worker, body)))
                elif op == 'publish':
                    pipe.send(('worker_response', _attempt(client, 'worker_submit', worker,
                                                          dict(body, assessment_digest=payload))))
                else:
                    raise Error('E_CHANNEL')
            if monitor:
                # An exact repeated admission checks public worker authority without renewing
                # the lease or permitting a second effect. E_CONFLICT is live, one-use authority.
                result = _attempt(client, 'worker_admit', worker, body)
                code = result.get('denied')
                if code == 'E_CONFLICT':
                    polls += 1
                    if polls == 1:
                        pipe.send(('monitoring', {'pid': os.getpid(), 'duplicateAdmission': code}))
                else:
                    require(code in ('E_AUTH', 'E_DENIED', 'E_STALE', 'E_UNRESOLVED'), 'E_ONE_USE')
                    pipe.send(('authority_loss', {'pid': os.getpid(), 'code': code, 'positivePolls': polls}))
                    monitor = False
        raise Error('E_MONITOR')


def collector_process(pipe):
    with closing(pipe):
        endpoint, collector = pipe.recv()
        client = CandidateClient(*endpoint)
        pipe.send(('ready', {'pid': os.getpid()}))
        while pipe.poll(150):
            op, payload = pipe.recv()
            if op == 'exit':
                return
            require(op == 'collect', 'E_CHANNEL')
            pipe.send(('collector_response', _attempt(client, 'collector_record', collector, payload)))
        raise Error('E_CHANNEL')


class Actor:
    def __init__(self, process, pipe):
        self.process, self.pipe = process, pipe
        self.pending = []

    def receive(self, event, timeout=20):
        deadline = time.monotonic() + timeout
        while True:
            for i, (name, value) in enumerate(self.pending):
                if name == event:
                    self.pending.pop(i)
                    return value
            require(self.pipe.poll(max(0, deadline - time.monotonic())), 'E_CHANNEL')
            self.pending.append(self.pipe.recv())

    def send(self, action, payload=None):
        self.pipe.send((action, payload))

    def join(self):
        self.process.join(10)
        require(self.process.exitcode == 0, 'E_ACTOR_EXIT')
        return {'pid': self.process.pid, 'exitCode': self.process.exitcode, 'alive': self.process.is_alive()}


@contextmanager
def actor(target, arguments):
    spawn = multiprocessing.get_context('spawn')
    parent, child = spawn.Pipe()
    with closing(parent), closing(child):
        process = spawn.Process(target=target, args=(child,))
        process.start()
        child.close()
        try:
            parent.send(arguments)
            yield Actor(process, parent)
        finally:
            if process.is_alive():
                process.terminate()
                process.join(10)
            require(not process.is_alive(), 'E_ACTOR_EXIT')
            process.close()
