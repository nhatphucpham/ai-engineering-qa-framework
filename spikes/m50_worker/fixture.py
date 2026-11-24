"""Isolated API1.1 bootstrap and non-secret database observations."""
from contextlib import closing, contextmanager
from dataclasses import dataclass
import secrets
import threading
import uuid

from runtime_candidate.application import Application, DEFAULT_CONFIG
from runtime_candidate.common import Error, digest, require
from runtime_candidate.fresh_fixture import source_intake
from runtime_candidate.transport import CandidateClient, serve

from .actors import request
from .controller import PROFILE


def deny(operation, *codes):
    try:
        operation()
    except (Error, RuntimeError) as exc:
        code = getattr(exc, 'code', str(exc))
        require(code in codes, 'E_WRONG_DENIAL')
        return code
    raise Error('E_NEGATIVE_ACCEPTED')


@dataclass
class Fixture:
    factory: object
    state_root: object
    schema: str
    endpoint: tuple
    client: CandidateClient
    scope: dict
    admin: str
    services: dict
    start: dict
    input_digest: str
    core_target: dict

    def request(self, op, token, **body):
        return request(self.client, op, token, **body)


@contextmanager
def fixture(work, certificate, key, forbidden, *, profile=PROFILE, lease=45, budget=90):
    schema, project, run_id = 'id_' + uuid.uuid4().hex, 'bridgeProject', 'bridge-' + uuid.uuid4().hex[:16]
    scope = {'project': project, 'run_id': run_id}
    state_root = work / schema
    factory = lambda: Application(schema, state_root)
    password, changed = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    forbidden.extend((password.encode(), changed.encode()))
    with closing(Application(schema, state_root, create=True)) as app:
        app.identity.bootstrap('admin', password)
    server = serve(factory, certificate, key)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    endpoint = ('127.0.0.1', server.server_address[1], certificate)
    client = CandidateClient(*endpoint)

    def login(secret):
        tokens = request(client, 'session_login', user='admin', password=secret)
        forbidden.extend(tokens[key].encode() for key in ('access', 'refresh'))
        return tokens['access']

    try:
        access = login(password)
        request(client, 'session_change_password', access, old=password, new=changed)
        admin = login(changed)
        request(client, 'project_create', admin, project=project, owner='admin')
        request(client, 'project_create', admin, project='otherProject', owner='admin')
        data = source_intake(project_id=project, task_id='bridgeTask', handoff_id='bridgeHandoff', run_id=run_id)
        manifest = data['manifest']
        if profile == PROFILE:
            manifest = dict(manifest, inputHashes={}, checkRegistry=PROFILE,
                            origin='fresh-source-context-bounded-resource-probe')
        with closing(factory()) as app:
            registered = app.register_snapshot(project, 'bridge_snapshot', 'repo_task', data['bundle'],
                                                sources=data['sources'], mode='executed_fixture', manifest=manifest)
            core_target = app.store.snapshot(project, 'bridge_snapshot')['manifest']['coreTarget']
        config = dict(DEFAULT_CONFIG, sourceIds=sorted(data['sources']), leaseSeconds=lease, runSeconds=budget)
        request(client, 'project_configure', admin, project=project, expected_config=1, config=config)
        grant = request(client, 'grant_issue', admin, project=project,
                        actions=['start', 'cancel', 'read', 'source', 'report', 'export', 'stream'], expected_config=2)['grant']
        forbidden.append(grant.encode())
        services = {}
        for name, kind, allowed in [('scheduler', 'scheduler', project), ('worker', 'worker', project),
                                    ('collector', 'collector', project), ('assessor', 'assessor', project),
                                    ('otherCollector', 'collector', 'otherProject')]:
            services[name] = request(client, 'service_enroll', admin, service=name, kind=kind, projects=[allowed])['credential']
            forbidden.append(services[name].encode())
        intake = request(client, 'intake_snapshot', admin, project=project, key='bridge_intake',
                         kind='repo_task', snapshot_ref='bridge_snapshot', expected_config=2,
                         candidate_digest=registered['candidateDigest'], input_digest=registered['inputDigest'])
        start = dict(scope, key='bridge_start', intake_id=intake['intakeId'], grant=grant, expected_config=2)
        yield Fixture(factory, state_root, schema, endpoint, client, scope, admin, services, start,
                      registered['inputDigest'], core_target)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(5)
        require(not thread.is_alive(), 'E_UNRESOLVED')


def graph(app, scope, *, inspect_fault=False):
    # The latter branch observes a fixture after intentional authority-file divergence. It is
    # restricted to a read-only diff of the DB fixture and cannot acknowledge an effect.
    locked = app.identity.tx if inspect_fault else app.store.unit
    with locked():
        run = app.store.run(scope['project'], scope['run_id'])
        params = (run['project'], run['id'])
        executions = app.conn.execute('''SELECT assignment,fence,effect_nonce,record_digest,work_accepted,collector
            FROM rt_executions WHERE project=%s AND run_id=%s ORDER BY assignment''', params).fetchall()
        totals = app.conn.execute('''SELECT
            (SELECT count(*) FROM rt_assessments WHERE (project,run_id)=(r.project,r.id)) AS assessments,
            (SELECT count(*) FROM rt_reports WHERE (project,run_id)=(r.project,r.id)) AS reports,
            (SELECT count(*) FROM rt_events WHERE (project,run_id)=(r.project,r.id) AND event='report_ready') AS ready
            FROM rt_runs r WHERE project=%s AND id=%s''', params).fetchone()
        events = app.conn.execute('''SELECT event,data FROM rt_events WHERE project=%s AND run_id=%s
            ORDER BY sequence''', params).fetchall()
        witness = run['effect_witness'] or {}
        return {'state': run['state'], 'version': run['version'], 'incident': run['incident'], 'fence': run['fence'],
                'assignment': run['assignment'], 'witnessSha256': digest(witness),
                'hasObservation': 'observation' in witness, 'executions': executions, **totals, 'events': events}
