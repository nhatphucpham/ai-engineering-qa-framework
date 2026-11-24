"""Durable synthetic inbox + explicit application admission; never provider proof.

Only trusted setup can register streams/proofs. Page data cannot register itself.
Each write transaction has ONE Store witness; API commands remain unchanged.
"""
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
import re

from runtime_candidate.common import VERSION as API_VERSION, Error, canonical, digest, exact, identifier, require
from runtime_candidate.storage import Denied, Jsonb, psycopg

VERSION = 'p4d-g1-1.0.0'


def positive(value):
    require(type(value) is int and 0 < value < 2**63)
    return value


def revision(value):
    require(isinstance(value, str) and re.fullmatch('[a-f0-9]{40}', value))
    return value


def token(value):
    require(isinstance(value, str) and re.fullmatch('[A-Za-z0-9][A-Za-z0-9._:-]{0,127}', value))
    return value


def access_shape(value):
    require(isinstance(value, str) and re.fullmatch(r'a\.[A-Za-z0-9_-]{43}', value), 'E_AUTH')


def observation(value):
    """Return receipt ID, repo, PR, unresolved reason; never an inferred binding."""
    exact(value, 'kind body')
    kind, body = value['kind'], value['body']
    require(isinstance(body, dict))
    try:
        repo, pr = positive(body['repository']['id']), positive(body['number'])
        if kind == 'webhook':
            require(body['action'] == 'ready_for_review')
            require(positive(body['pull_request']['number']) == pr)
            revision(body['pull_request']['head']['sha'])
            return 'webhook:' + token(body['delivery']), repo, pr, 'missing_common_occurrence'
        if kind == 'timeline':
            require(type(body['historyComplete']) is bool)
            require(body['event']['event'] == 'ready_for_review')
            event = positive(body['event']['id'])
            return 'timeline:' + str(event), repo, pr, ('missing_exact_event_revision' if body['historyComplete'] else 'history_gap')
        require(kind == 'snapshot')
        revision(body['head']['sha'])
        require(type(body['draft']) is bool and type(body['historyComplete']) is bool)
        return 'snapshot:' + digest(body), repo, pr, ('missing_transition' if body['historyComplete'] else 'history_gap')
    except (KeyError, TypeError):
        raise Error() from None


def page(value):
    exact(value, 'version project stream expected next observations')
    require(value['version'] == VERSION, 'E_VERSION')
    identifier(value['project']); identifier(value['stream'])
    require(type(value['expected']) is int and 0 <= value['expected'] < 2**63 - 1)
    require(type(value['next']) is int and value['next'] == value['expected'] + 1)
    require(isinstance(value['observations'], list) and 1 <= len(value['observations']) <= 64)
    require(len(canonical(value)) <= 65536)
    seen = {}
    for obs in value['observations']:
        rid, *_ = observation(obs)
        require(rid not in seen or seen[rid] == digest(obs), 'E_CONFLICT')
        seen[rid] = digest(obs)
    return value


class Ingress:
    def __init__(self, app, *, create=False):
        self.app, self.store, self.conn = app, app.store, app.conn
        if create:
            with self.store.unit(write=True):
                self.conn.execute((Path(__file__).parent / 'schema.sql').read_text(encoding='utf-8'))
        require(self.conn.execute('SELECT * FROM g1_control').fetchall() == [{'version': VERSION}], 'E_VERSION')

    @contextmanager
    def safe(self):
        try:
            yield
        except Error:
            raise
        except Denied as exc:
            raise Error(exc.code) from None
        except psycopg.Error:
            raise Error('E_DEPENDENCY') from None

    def register_stream(self, project, stream, repo, pr, actor, grant, expected_config, sources):
        """Operator setup only, no public route. Immutable dummy integration authority."""
        for value in (project, stream, actor):
            identifier(value)
        positive(repo); positive(pr); positive(expected_config)
        require(isinstance(sources, list) and sources and len(sources) == len(set(sources)))
        for source in sources:
            identifier(source)
        with self.safe(), self.store.unit(write=True):
            self.conn.execute('INSERT INTO g1_streams(project,id,repo,pr,actor,grant_id,config,sources) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)',
                              (project, stream, repo, pr, actor, grant, expected_config, Jsonb(sorted(sources))))

    def stream(self, project, stream):
        row = self.conn.execute('SELECT * FROM g1_streams WHERE project=%s AND id=%s', (project, stream)).fetchone()
        require(row is not None, 'E_DENIED')
        return row

    def authority(self, actor, stream, deadlines):
        require(actor['id'] == stream['actor'], 'E_DENIED')
        config, _, _ = self.store.grant(actor, stream['project'], stream['grant_id'], 'start', deadlines)
        require(config['config_version'] == stream['config'], 'E_STALE')
        require(set(stream['sources']) <= set(config['payload']['sourceIds']), 'E_DENIED')
        return config

    def snapshot(self, project, plan):
        snap = self.store.snapshot(project, plan['snapshot'])
        target = snap['manifest']['coreTarget']
        require(snap['kind'] == 'repo_task' and snap['manifest']['run_id'] == plan['run']
                and target['candidateRevision'] == plan['revision']
                and snap['candidate_digest'] == plan['candidateDigest'] and snap['input_digest'] == plan['inputDigest'], 'E_INTEGRITY')
        return snap

    def register_proof(self, project, stream, obs, *, occurrence, revision_sha, snapshot, run):
        """Authored fixture pairing only; a hash does not attest to GitHub provenance."""
        rid, repo, pr, reason = observation(obs)
        token(occurrence); revision(revision_sha); identifier(snapshot); identifier(run)
        require(obs['kind'] != 'snapshot' and reason != 'history_gap')
        if obs['kind'] == 'webhook':
            require(obs['body']['pull_request']['head']['sha'] == revision_sha, 'E_INTEGRITY')
        else:
            require(occurrence == rid, 'E_INTEGRITY')
        with self.safe(), self.store.unit(write=True):
            stream_row = self.stream(project, stream)
            require((repo, pr) == (stream_row['repo'], stream_row['pr']), 'E_DENIED')
            snap = self.store.snapshot(project, snapshot)
            plan = {'mode': 'trusted_synthetic_pairing', 'occurrence': occurrence, 'revision': revision_sha,
                    'snapshot': snapshot, 'run': run, 'candidateDigest': snap['candidate_digest'], 'inputDigest': snap['input_digest']}
            self.snapshot(project, plan)
            self.conn.execute('INSERT INTO g1_proofs VALUES(%s,%s,%s,%s)', (project, stream, digest(obs), Jsonb(plan)))
        return plan

    @staticmethod
    def binding_id(project, stream, occurrence):
        return digest([project, stream['repo'], stream['pr'], 'pr_ready', occurrence])

    def receive(self, access, value):
        access_shape(access)
        value = deepcopy(value)
        page(value)
        project, stream_id = value['project'], value['stream']
        with self.safe(), self.store.unit(access, write=True) as (actor, deadlines):
            stream = self.stream(project, stream_id)
            self.authority(actor, stream, deadlines)
            previous = self.conn.execute('SELECT * FROM g1_pages WHERE project=%s AND stream=%s AND predecessor=%s',
                                         (project, stream_id, value['expected'])).fetchone()
            if previous:
                require(previous['digest'] == digest(value), 'E_CONFLICT')
                return previous['result']
            require(value['expected'] == stream['cursor'], 'E_STALE')
            # Read/validate every observation before the first ledger mutation.
            prepared = []
            for obs in value['observations']:
                rid, repo, pr, reason = observation(obs)
                require((repo, pr) == (stream['repo'], stream['pr']), 'E_DENIED')
                old = self.conn.execute('SELECT * FROM g1_receipts WHERE project=%s AND stream=%s AND id=%s', (project, stream_id, rid)).fetchone()
                require(old is None or old['digest'] == digest(obs), 'E_CONFLICT')
                proof = self.conn.execute('SELECT plan FROM g1_proofs WHERE project=%s AND stream=%s AND observation_digest=%s',
                                         (project, stream_id, digest(obs))).fetchone()
                prepared.append((obs, rid, reason, old, proof))
            results = []
            for obs, rid, reason, old, proof in prepared:
                old = self.conn.execute('SELECT * FROM g1_receipts WHERE project=%s AND stream=%s AND id=%s', (project, stream_id, rid)).fetchone()
                if old:
                    results.append({'receipt': rid, 'status': old['status'], 'binding': old['binding']})
                    continue
                bid, status = None, 'unresolved'
                if proof:
                    plan = proof['plan']
                    bid = self.binding_id(project, stream, plan['occurrence'])
                    binding = self.conn.execute('SELECT * FROM g1_bindings WHERE project=%s AND id=%s', (project, bid)).fetchone()
                    if binding and (binding['quarantined'] or binding['plan'] != plan):
                        self.conn.execute('UPDATE g1_bindings SET quarantined=true WHERE project=%s AND id=%s', (project, bid))
                        self.conn.execute("UPDATE g1_receipts SET status='quarantined',reason='binding_conflict' WHERE project=%s AND binding=%s", (project, bid))
                        status, reason = 'quarantined', 'binding_conflict'
                    elif binding:
                        status, reason = 'duplicate', None
                    else:
                        # Reject a reused run across distinct occurrences before writing a plan.
                        require(not self.conn.execute("SELECT 1 FROM g1_bindings WHERE project=%s AND plan->>'run'=%s", (project, plan['run'])).fetchone(), 'E_CONFLICT')
                        self.conn.execute('INSERT INTO g1_bindings(project,id,stream,plan) VALUES(%s,%s,%s,%s)', (project, bid, stream_id, Jsonb(plan)))
                        status, reason = 'pending', None
                self.conn.execute('INSERT INTO g1_receipts VALUES(%s,%s,%s,%s,%s,%s,%s,%s)',
                                  (project, stream_id, rid, digest(obs), canonical(obs), status, reason, bid))
                results.append({'receipt': rid, 'status': status, 'binding': bid})
            result = {'cursor': value['next'], 'observations': results}
            self.conn.execute('INSERT INTO g1_pages VALUES(%s,%s,%s,%s,%s)', (project, stream_id, value['expected'], digest(value), Jsonb(result)))
            self.conn.execute('UPDATE g1_streams SET cursor=%s WHERE project=%s AND id=%s', (value['next'], project, stream_id))
            return result

    def command(self, operation, access, **params):
        return self.app.dispatch(operation, access, dict(params, version=API_VERSION))

    def guarded(self, access, project, bid, phase, intake_id=None):
        access_shape(access)
        # Outer identity lock only: the inner dispatch is the sole witness write.
        held_deadlines = []
        def check_deadlines():
            if held_deadlines:
                require(self.conn.execute('SELECT %s>clock_timestamp() AS live', (min(held_deadlines),)).fetchone()['live'], 'E_DENIED')
        with self.safe(), self.app.identity.tx(access, before_finish=check_deadlines):
            with self.store.unit(access) as (actor, deadlines):
                binding = self.conn.execute('SELECT * FROM g1_bindings WHERE project=%s AND id=%s', (project, bid)).fetchone()
                require(binding is not None and not binding['quarantined'], 'E_UNRESOLVED')
                stream = self.stream(project, binding['stream'])
                config = self.authority(actor, stream, deadlines)
                held_deadlines.extend(deadlines)
                plan = binding['plan']; snapshot = self.snapshot(project, plan)
                self.store.source_scope(snapshot, config)
                require(snapshot['manifest']['coreTarget']['projectConfigVersion'] == config['config_version']
                        and snapshot['manifest']['coreTarget']['dataPolicyVersion'] == config['policy_version'], 'E_STALE')
                intake_params = dict(project=project, key='i_' + bid[:60], kind='repo_task', snapshot_ref=plan['snapshot'],
                                     candidate_digest=plan['candidateDigest'], input_digest=plan['inputDigest'], expected_config=stream['config'])
                prior = self.store.prior(actor, project, 'intake_snapshot', intake_params['key'], intake_params)
                expected_start = dict(project=project, key='s_' + bid[:60], run_id=plan['run'],
                                      intake_id=prior['intakeId'] if prior else None,
                                      grant=stream['grant_id'], expected_config=stream['config'])
                start_receipt = self.conn.execute('SELECT * FROM rt_receipts WHERE actor=%s AND project=%s AND key=%s',
                                                  (actor['id'], project, expected_start['key'])).fetchone()
                if start_receipt is not None:
                    require(prior is not None, 'E_CONFLICT')
                    self.store.prior(actor, project, 'run_start', expected_start['key'], expected_start)
                if phase == 'intake':
                    params, op = intake_params, 'intake_snapshot'
                    # API exact prior receipt bypasses only new-work checks, never authorization.
                    if prior is None:
                        require(not self.conn.execute('SELECT 1 FROM rt_runs WHERE project=%s AND id=%s', (project, plan['run'])).fetchone(), 'E_CONFLICT')
                        count = self.conn.execute("SELECT count(*) AS n FROM rt_runs WHERE project=%s AND state='queued'", (project,)).fetchone()['n']
                        require(count < config['payload']['maxQueued'], 'E_BUDGET')
                else:
                    require(phase == 'start' and prior is not None and prior['intakeId'] == intake_id, 'E_INTEGRITY')
                    op = 'run_start'
                    params = dict(project=project, key='s_' + bid[:60], run_id=plan['run'], intake_id=intake_id,
                                  grant=stream['grant_id'], expected_config=stream['config'])
            return self.command(op, access, **params)

    def drain(self, access, project, bid, *, after_start=None):
        access_shape(access)
        identifier(project)
        require(isinstance(bid, str) and re.fullmatch('[a-f0-9]{64}', bid))
        intake = self.guarded(access, project, bid, 'intake')
        result = self.guarded(access, project, bid, 'start', intake['intakeId'])
        if after_start is not None:
            after_start()  # Trusted fault hook only; never page data.
        with self.safe(), self.store.unit(access, write=True) as (actor, deadlines):
            row = self.conn.execute('SELECT * FROM g1_bindings WHERE project=%s AND id=%s', (project, bid)).fetchone()
            self.authority(actor, self.stream(project, row['stream']), deadlines)
            require(row['result'] is None or row['result'] == result, 'E_INTEGRITY')
            self.conn.execute('UPDATE g1_bindings SET result=%s WHERE project=%s AND id=%s', (Jsonb(result), project, bid))
        return result
