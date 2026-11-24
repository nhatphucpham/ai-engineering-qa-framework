"""Actual application dispatch / PostgreSQL acceptance. No QA/model execution."""
from copy import deepcopy
import json
from pathlib import Path
import secrets
import subprocess
import sys
import uuid

from runtime_candidate.application import Application, DEFAULT_CONFIG
from runtime_candidate.common import Error, canonical, digest, require
from runtime_candidate.fresh_fixture import source_intake
from .ingress import Ingress
from .test_ingress import SHA_A, SHA_B, webhook, timeline, snapshot, make_page


class Cases:
    def __init__(self, workspace, checks, forbidden):
        self.workspace, self.checks, self.forbidden = workspace, checks, forbidden
        self.schema = 'id_' + uuid.uuid4().hex
        self.root = workspace / self.schema
        self.app = Application(self.schema, self.root, create=True)
        pw, new = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        forbidden.extend((pw.encode(), new.encode()))
        self.app.identity.bootstrap('admin', pw)
        first = self.call('session_login', None, user='admin', password=pw)
        self.call('session_change_password', first['access'], old=pw, new=new)
        self.admin = self.call('session_login', None, user='admin', password=new)['access']
        self.forbidden.append(self.admin.encode())
        self.call('account_create', self.admin, user='runner', password=pw)
        first = self.call('session_login', None, user='runner', password=pw)
        self.call('session_change_password', first['access'], old=pw, new=new)
        self.runner = self.call('session_login', None, user='runner', password=new)['access']
        self.forbidden.append(self.runner.encode())
        self.ingress = Ingress(self.app, create=True)

    def call(self, op, access, **params):
        from runtime_candidate.common import VERSION
        return self.app.dispatch(op, access, dict(params, version=VERSION))

    def scope(self, *, max_queued=20):
        project = 'p_' + uuid.uuid4().hex
        self.call('project_create', self.admin, project=project, owner='admin')
        self.call('account_set_role', self.admin, project=project, user='runner', role='Runner')
        self.register_input(project)  # Source IDs must exist before the API enables their scope.
        config = dict(DEFAULT_CONFIG, sourceIds=['artifact-' + str(n) for n in range(1, 9)], maxQueued=max_queued)
        self.call('project_configure', self.admin, project=project, expected_config=1, config=config)
        grant = self.call('grant_issue', self.runner, project=project, actions=['start'], expected_config=2)['grant']
        self.ingress.register_stream(project, 'main', 101, 7, 'runner', grant, 2, config['sourceIds'])
        return project, grant, config

    def register_input(self, project, sha=SHA_A, *, run=None, snap=None, config_version=2, policy_version=2):
        run = run or 'run_' + uuid.uuid4().hex
        snap = snap or 'snap_' + uuid.uuid4().hex
        data = source_intake(project_id=project, task_id='task_' + uuid.uuid4().hex,
                             handoff_id='handoff_' + uuid.uuid4().hex, run_id=run,
                             config_version=config_version, policy_version=policy_version)
        # New synthetic registration only; no fetched Git commit / historical evidence.
        data['bundle'] = json.loads(canonical(data['bundle']).decode('utf-8').replace('mock-06-head-v1', sha))
        data['sources'] = {key: (raw, cls, sha if rev == 'mock-06-head-v1' else rev)
                           for key, (raw, cls, rev) in data['sources'].items()}
        self.app.register_snapshot(project, snap, 'repo_task', data['bundle'], sources=data['sources'],
                                   mode='imported', manifest={'origin': 'g1-authored-source-only-no-provider-proof'})
        return snap, run

    def proof(self, project, obs, occurrence='timeline:1', sha=SHA_A, *, run=None, snap=None):
        snap, run = self.register_input(project, sha, run=run, snap=snap)
        plan = self.ingress.register_proof(project, 'main', obs, occurrence=occurrence,
                                           revision_sha=sha, snapshot=snap, run=run)
        return plan

    def alias_proof(self, project, obs, plan):
        return self.ingress.register_proof(project, 'main', obs, occurrence=plan['occurrence'],
                                          revision_sha=plan['revision'], snapshot=plan['snapshot'], run=plan['run'])

    def counts(self, project):
        tables = ('g1_receipts', 'g1_bindings', 'g1_pages', 'rt_intakes', 'rt_runs', 'rt_events', 'rt_receipts')
        return {table: self.app.conn.execute('SELECT count(*) AS n FROM ' + table + ' WHERE project=%s', (project,)).fetchone()['n'] for table in tables}

    def check_error(self, code, action):
        try:
            action()
        except Error as exc:
            require(exc.code == code, 'E_INTEGRITY')
        else:
            raise Error('E_INTEGRITY')

    def receive(self, project, observations, expected=0, access=None):
        return self.ingress.receive(access or self.runner, make_page(project, observations, expected))

    def binding(self, project, result):
        return self.app.conn.execute('SELECT * FROM g1_bindings WHERE project=%s AND id=%s',
                                     (project, result['observations'][0]['binding'])).fetchone()

    def passed(self, key, **facts):
        self.checks[key] = dict(status='PASS', **facts)

    def run(self):
        # C01: unproved facts cannot create intake even if a provider-looking claim is present.
        p, _, _ = self.scope()
        wh = webhook(); wh['body'].update(proof={'mode': 'provider_verified'}, currentHead=SHA_B)
        result = self.receive(p, [wh, timeline(), snapshot(), timeline(2, complete=False), snapshot(False)])
        require(all(row['status'] == 'unresolved' for row in result['observations']))
        require(self.counts(p)['rt_intakes'] == self.counts(p)['rt_runs'] == 0)
        require(self.app.conn.execute("SELECT count(*) AS n FROM g1_receipts WHERE project=%s AND reason='history_gap'", (p,)).fetchone()['n'] == 2)
        self.passed('C01', unprovedObservations=5, historyGaps=2, intakes=0, runs=0, claimedProofIgnored=True)

        # C02: exact pair, delivery repetition, two wrapper instances, one occurrence.
        p, _, _ = self.scope()
        wh, poll = webhook(), timeline()
        plan = self.proof(p, wh); self.alias_proof(p, poll, plan)
        result = self.receive(p, [wh, poll, deepcopy(wh)])
        bid = result['observations'][0]['binding']
        require([r['binding'] for r in result['observations']] == [bid, bid, bid])
        require(result['observations'][1]['status'] == 'duplicate')
        persisted = self.app.conn.execute('SELECT id,status,binding FROM g1_receipts WHERE project=%s ORDER BY id', (p,)).fetchall()
        require(len(persisted) == 2 and {r['binding'] for r in persisted} == {bid})
        require({r['id']: r['status'] for r in persisted} == {'timeline:1': 'duplicate', 'webhook:d1': 'pending'})
        accepted = self.ingress.drain(self.runner, p, bid)
        require(accepted['runId'] == plan['run'])
        require(self.call('run_read', self.runner, project=p, run_id=plan['run'])['state'] == 'queued')
        events = self.call('events', self.runner, project=p, run_id=plan['run'], after=0)
        require(events == {'events': [{'id': 1, 'event': 'run_state', 'data': {'state': 'queued', 'stateVersion': 1}}]})
        require(self.counts(p)['rt_intakes'] == self.counts(p)['rt_runs'] == self.counts(p)['rt_events'] == 1)
        require(self.binding(p, result)['plan'] == plan)
        before = self.counts(p)
        require(self.receive(p, [wh, poll, deepcopy(wh)]) == result)
        require(self.ingress.drain(self.runner, p, bid) == accepted and self.counts(p) == before)
        self.passed('C02', receipts=2, intakes=1, runs=1, initialEvents=1, operatorPlan=plan, ordinaryEvents=events)

        # C03: same SHA has two independent occurrence/run identities.
        second = webhook('d2'); second_plan = self.proof(p, second, 'timeline:2')
        result2 = self.receive(p, [second], 1)
        self.ingress.drain(self.runner, p, result2['observations'][0]['binding'])
        require(plan['revision'] == second_plan['revision'] and plan['run'] != second_plan['run'])
        require(self.counts(p)['rt_runs'] == self.counts(p)['rt_events'] == 2)
        self.passed('C03', sameSyntheticSha=True, distinctOccurrences=2, runs=2)

        # C04: revision contradiction and sticky quarantine, prior run preserved.
        conflict = webhook('d3', SHA_B)
        self.proof(p, conflict, 'timeline:1', SHA_B)
        before = self.counts(p)
        result3 = self.receive(p, [conflict], 2)
        require(result3['observations'][0]['status'] == 'quarantined')
        correct = webhook('d4'); self.alias_proof(p, correct, plan)
        require(self.receive(p, [correct], 3)['observations'][0]['status'] == 'quarantined')
        self.check_error('E_UNRESOLVED', lambda: self.ingress.drain(self.runner, p, bid))
        require(self.counts(p)['rt_runs'] == before['rt_runs'] and self.counts(p)['rt_intakes'] == before['rt_intakes'])
        require(self.binding(p, result3)['plan'] == plan)
        self.passed('C04', originalBindingAndRunRetained=True, quarantineSticky=True, additionalRuns=0)

        # C05: same revision / different snapshot is also contradiction.
        p, _, _ = self.scope(); wh = webhook(); plan = self.proof(p, wh)
        result = self.receive(p, [wh]); bid = result['observations'][0]['binding']
        changed = webhook('d5'); self.proof(p, changed)
        require(self.receive(p, [changed], 1)['observations'][0]['status'] == 'quarantined')
        self.check_error('E_UNRESOLVED', lambda: self.ingress.drain(self.runner, p, bid))
        require(self.counts(p)['rt_intakes'] == self.counts(p)['rt_runs'] == 0)
        self.passed('C05', sameRevisionDifferentSnapshotQuarantined=True, intakes=0, runs=0)

        # C06: proof registry is exact; wrong subjects/heads/event identity reject.
        p, _, _ = self.scope(); wh = webhook(); plan = self.proof(p, wh)
        altered = deepcopy(wh); altered['body']['currentHead'] = SHA_B
        require(self.receive(p, [altered])['observations'][0]['status'] == 'unresolved')
        self.check_error('E_INTEGRITY', lambda: self.alias_proof(p, webhook('d6', SHA_B), plan))
        self.check_error('E_INTEGRITY', lambda: self.alias_proof(p, timeline(9), plan))
        before = self.counts(p)
        for bad in (webhook(repo=102), webhook(pr=8)):
            self.check_error('E_DENIED', lambda: self.receive(p, [bad], 1))
        self.check_error('E_DENIED', lambda: self.receive(p, [wh], 1, self.admin))
        require(self.counts(p) == before)
        q, _, _ = self.scope()
        # A registration for p cannot resolve identical bytes under q.
        require(self.receive(q, [wh])['observations'][0]['status'] == 'unresolved')
        self.passed('C06', exactObservationDigest=True, wrongHeadEventSubjectActorDenied=True, projectIsolation=True)

        # C07: mixed bad page and changed receipt cannot poison current authority.
        p, _, _ = self.scope(); wh = webhook(); self.proof(p, wh)
        changed = deepcopy(wh); changed['body']['untrusted'] = 'changed'
        before = self.counts(p)
        self.check_error('E_CONFLICT', lambda: self.receive(p, [wh, changed]))
        require(self.counts(p) == before)
        result = self.receive(p, [wh])
        before = self.counts(p)
        self.check_error('E_CONFLICT', lambda: self.receive(p, [webhook('new'), changed], 1))
        require(self.counts(p) == before)
        require(self.receive(p, [webhook('new')], 1)['cursor'] == 2)
        self.call('project_read', self.runner, project=p)
        self.passed('C07', rejectedMixedPages=2, nextValidPageAndRead=True, rejectedPagesNoEffects=True)

        # C08: cursor replay/loss after receive in a separate process; queue self-full replay.
        p, _, _ = self.scope(max_queued=1); wh = webhook(); plan = self.proof(p, wh)
        result = self.receive(p, [wh]); bid = result['observations'][0]['binding']
        wire = self.workspace / 'private-replay.json'
        wire.write_bytes(canonical({'schema': self.schema, 'root': str(self.root), 'access': self.runner,
                                   'page': make_page(p, [wh]), 'binding': bid}))
        self.forbidden.append(wire.read_bytes())
        self.app.close()
        proc = subprocess.run([sys.executable, '-B', '-m', 'spikes.p4d_g1.replay_process', str(wire)],
                              capture_output=True, timeout=25, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        require(proc.returncode == 0, 'E_INTEGRITY')
        self.app = Application(self.schema, self.root); self.ingress = Ingress(self.app)
        require(self.binding(p, result)['result'] is None)
        before = self.counts(p)
        accepted = self.ingress.drain(self.runner, p, bid)
        require(self.counts(p) == before and accepted['runId'] == plan['run'])
        self.check_error('E_STALE', lambda: self.receive(p, [webhook('ahead')], 8))
        self.check_error('E_CONFLICT', lambda: self.receive(p, [webhook('changed')]))
        require(self.receive(p, [timeline(8, complete=False)], 1)['cursor'] == 2)
        self.passed('C08', childExit=proc.returncode, lostReceiveResponseReplay=True, lostStartResponseBeforeMarker=True,
                    queueMax=1, queueOccupiedByOwnRun=True, sameCountsAfterReplay=True)

        # C09: full queue blocks NEW intake, and does not corrupt authority.
        second = webhook('new-work'); self.proof(p, second, 'timeline:2')
        next_result = self.receive(p, [second], 2)
        before = self.counts(p)
        self.check_error('E_BUDGET', lambda: self.ingress.drain(self.runner, p, next_result['observations'][0]['binding']))
        require(self.counts(p) == before)
        self.call('run_read', self.runner, project=p, run_id=plan['run'])
        self.passed('C09', capacityDenialBeforeIntake=True, nextReadUsable=True)

        # C10: grant revoke before receive/drain/replay has zero new effects.
        p, grant, _ = self.scope(); wh = webhook(); self.proof(p, wh)
        result = self.receive(p, [wh]); bid = result['observations'][0]['binding']
        self.call('grant_revoke', self.runner, project=p, grant=grant)
        before = self.counts(p)
        for action in (lambda: self.receive(p, [wh]), lambda: self.receive(p, [webhook('new')], 1),
                       lambda: self.ingress.drain(self.runner, p, bid)):
            self.check_error('E_DENIED', action)
        require(self.counts(p) == before and before['rt_intakes'] == 0)
        self.passed('C10', revokedReceiveReplayDrainDenied=True, zeroNewEffects=True)

        # C11: role/config/source/enabled denials, each in fresh project.
        for change in ('role', 'config', 'source', 'disabled'):
            p, _, cfg = self.scope(); wh = webhook(); self.proof(p, wh)
            result = self.receive(p, [wh]); bid = result['observations'][0]['binding']
            if change == 'role':
                self.call('account_set_role', self.admin, project=p, user='runner', role='Viewer')
            else:
                cfg = dict(cfg)
                if change == 'source': cfg['sourceIds'] = []
                elif change == 'disabled': cfg['enabled'] = False
                else: cfg['maxQueued'] = 21
                self.call('project_configure', self.admin, project=p, expected_config=2, config=cfg)
            before = self.counts(p)
            self.check_error('E_DENIED', lambda: self.ingress.drain(self.runner, p, bid))
            self.check_error('E_DENIED', lambda: self.receive(p, [wh]))
            require(self.counts(p) == before and before['rt_intakes'] == 0)
        self.passed('C11', roleConfigSourceDisabledDenials=4, zeroNewIntakes=True)

        # C14: project-wide run uniqueness includes DIFFERENT repo streams.
        p, grant, _ = self.scope(); wh = webhook(); plan = self.proof(p, wh)
        self.receive(p, [wh])
        self.ingress.register_stream(p, 'other', 102, 8, 'runner', grant, 2, ['artifact-' + str(n) for n in range(1, 9)])
        other = webhook('otherDelivery', repo=102, pr=8)
        self.ingress.register_proof(p, 'other', other, occurrence='timeline:99', revision_sha=SHA_A,
                                    snapshot=plan['snapshot'], run=plan['run'])
        wrong = make_page(p, [other]); wrong['stream'] = 'other'
        before = self.counts(p)
        self.check_error('E_CONFLICT', lambda: self.ingress.receive(self.runner, wrong))
        require(self.counts(p) == before)
        valid = webhook('unprovedOther', repo=102, pr=8)
        good = make_page(p, [valid]); good['stream'] = 'other'
        require(self.ingress.receive(self.runner, good)['cursor'] == 1)
        self.call('project_read', self.runner, project=p)
        self.passed('C14', crossStreamRunReuseDeniedBeforeAdmission=True, unchangedCounts=True, nextPageAndReadUsable=True)

        # C15: current grant/config valid, independently deny stream and snapshot data scope.
        p, _, cfg = self.scope()
        cfg = dict(cfg, sourceIds=cfg['sourceIds'][:-1])
        self.call('project_configure', self.admin, project=p, expected_config=2, config=cfg)
        grant = self.call('grant_issue', self.runner, project=p, actions=['start'], expected_config=3)['grant']
        self.ingress.register_stream(p, 'denied', 103, 7, 'runner', grant, 3, ['artifact-' + str(n) for n in range(1, 9)])
        denied = make_page(p, [webhook(repo=103)]); denied['stream'] = 'denied'
        before = self.counts(p)
        self.check_error('E_DENIED', lambda: self.ingress.receive(self.runner, denied))
        require(self.counts(p) == before)
        self.ingress.register_stream(p, 'scoped', 102, 7, 'runner', grant, 3, cfg['sourceIds'])
        snap, run = self.register_input(p, config_version=3, policy_version=3)
        scoped = webhook(repo=102)
        self.ingress.register_proof(p, 'scoped', scoped, occurrence='timeline:1', revision_sha=SHA_A, snapshot=snap, run=run)
        wire_page = make_page(p, [scoped]); wire_page['stream'] = 'scoped'
        result = self.ingress.receive(self.runner, wire_page)
        require(self.ingress.receive(self.runner, wire_page) == result)  # Current grant authorizes inbox replay.
        before = self.counts(p)
        self.check_error('E_DENIED', lambda: self.ingress.drain(self.runner, p, result['observations'][0]['binding']))
        require(self.counts(p) == before and before['rt_intakes'] == 0)
        self.call('project_read', self.runner, project=p)
        self.passed('C15', currentGrantConfig=3, streamScopeDenied=True, snapshotScopeDeniedBeforeIntake=True,
                    authorizedInboxReplay=True, nextReadUsable=True)

        # C16: deterministic start key conflict must reject BEFORE a new intake.
        p, _, _ = self.scope(); planned = webhook(); plan = self.proof(p, planned)
        result = self.receive(p, [planned]); bid = result['observations'][0]['binding']
        other_snap, _ = self.register_input(p)
        registered = self.app.store.snapshot(p, other_snap)
        self.call('intake_snapshot', self.runner, project=p, key='s_' + bid[:60], kind='repo_task', snapshot_ref=other_snap,
                  candidate_digest=registered['candidate_digest'], input_digest=registered['input_digest'], expected_config=2)
        before = self.counts(p)
        self.check_error('E_CONFLICT', lambda: self.ingress.drain(self.runner, p, bid))
        require(self.counts(p) == before and before['rt_runs'] == 0)
        self.check_error('E_DENIED', lambda: self.ingress.drain(self.admin, p, bid))
        # Different snapshot consumes the intake key, still no second intake/run.
        q, _, _ = self.scope(); plan2 = self.proof(q, webhook())
        result2 = self.receive(q, [webhook()]); bid2 = result2['observations'][0]['binding']
        other_snap, _ = self.register_input(q)
        registered = self.app.store.snapshot(q, other_snap)
        self.call('intake_snapshot', self.runner, project=q, key='i_' + bid2[:60], kind='repo_task', snapshot_ref=other_snap,
                  candidate_digest=registered['candidate_digest'], input_digest=registered['input_digest'], expected_config=2)
        before2 = self.counts(q)
        self.check_error('E_CONFLICT', lambda: self.ingress.drain(self.runner, q, bid2))
        require(self.counts(q) == before2)
        self.call('project_read', self.runner, project=q)
        self.passed('C16', conflictingStartKeyDeniedBeforeNewIntake=True, differentSnapshotIntakeKeyDenied=True,
                    wrongActorReplayDenied=True, usableAfterConflict=True)

        # C17: an existing run owned by another authorized principal is not replay.
        p, _, _ = self.scope(); plan = self.proof(p, webhook())
        result = self.receive(p, [webhook()]); bid = result['observations'][0]['binding']
        admin_grant = self.call('grant_issue', self.admin, project=p, actions=['start'], expected_config=2)['grant']
        intake = self.call('intake_snapshot', self.admin, project=p, key='other_owner_intake', kind='repo_task',
                           snapshot_ref=plan['snapshot'], candidate_digest=plan['candidateDigest'], input_digest=plan['inputDigest'], expected_config=2)
        self.call('run_start', self.admin, project=p, key='other_owner_start', run_id=plan['run'],
                  intake_id=intake['intakeId'], grant=admin_grant, expected_config=2)
        before = self.counts(p)
        self.check_error('E_CONFLICT', lambda: self.ingress.drain(self.runner, p, bid))
        require(self.counts(p) == before and before['rt_intakes'] == before['rt_runs'] == 1)
        require(self.receive(p, [webhook('afterCollision')], 1)['cursor'] == 2)
        self.passed('C17', existingRunOtherOwnerDeniedBeforeNewIntake=True, nextPageUsable=True)

        # C18: opaque UTF-8 JSON includes escaped NUL keys/values; preserve canonical bytes.
        p, _, _ = self.scope(); obs = webhook()
        obs['body']['opaque'] = {'nul\x00key': 'value\x00雪'}
        result = self.receive(p, [obs])
        row = self.app.conn.execute('SELECT observation,digest FROM g1_receipts WHERE project=%s', (p,)).fetchone()
        require(bytes(row['observation']) == canonical(obs) and row['digest'] == digest(obs))
        require(self.receive(p, [obs]) == result and self.counts(p)['rt_intakes'] == 0)
        self.passed('C18', escapedNulKeyAndValue=True, exactCanonicalUtf8Stored=True, replayStable=True)

        # C19: no session must deny consistently before receipt intake/replay/drain.
        p, _, _ = self.scope(); self.proof(p, webhook())
        wire_page = make_page(p, [webhook()]); result = self.ingress.receive(self.runner, wire_page)
        bid = result['observations'][0]['binding']; before = self.counts(p)
        for missing in (None, '', False, 'malformed'):
            self.check_error('E_AUTH', lambda: self.ingress.receive(missing, wire_page))
            self.check_error('E_AUTH', lambda: self.ingress.drain(missing, p, bid))
        require(self.counts(p) == before and before['rt_intakes'] == 0)
        self.passed('C19', missingSessionReceiveReplayDrainDenied=True, invalidSessionShapes=4, zeroEffects=True)

        # C12: revoked session plus absent stream reject without creating records.
        p, _, _ = self.scope()
        bad_page = make_page(p, [webhook()]); bad_page['stream'] = 'absent'
        self.check_error('E_DENIED', lambda: self.ingress.receive(self.runner, bad_page))
        before = self.counts(p)
        self.call('session_logout', self.runner)
        self.check_error('E_AUTH', lambda: self.receive(p, [webhook()]))
        require(self.counts(p) == before)
        self.passed('C12', revokedSessionAndAbsentStreamDenied=True)

        # C13: actual run/event/start-receipt write rolls back after witness failure.
        p = 'incident_' + uuid.uuid4().hex
        self.call('project_create', self.admin, project=p, owner='admin')
        self.register_input(p)
        cfg = dict(DEFAULT_CONFIG, sourceIds=['artifact-' + str(n) for n in range(1, 9)])
        self.call('project_configure', self.admin, project=p, expected_config=1, config=cfg)
        grant = self.call('grant_issue', self.admin, project=p, actions=['start'], expected_config=2)['grant']
        self.ingress.register_stream(p, 'main', 101, 7, 'admin', grant, 2, cfg['sourceIds'])
        plan = self.proof(p, webhook())
        result = self.receive(p, [webhook()], access=self.admin)
        bid = result['observations'][0]['binding']
        intake = self.ingress.guarded(self.admin, p, bid, 'intake')
        before = self.counts(p)
        require(before['rt_intakes'] == 1 and before['rt_receipts'] == 1 and before['rt_runs'] == before['rt_events'] == 0)
        def injected(stage):
            if stage == 'authority_witness_written':
                raise RuntimeError('G1_INJECTED_PRECOMMIT')
        self.app.store.observer = injected
        try:
            self.ingress.guarded(self.admin, p, bid, 'start', intake['intakeId'])
        except RuntimeError as exc:
            require(str(exc) == 'G1_INJECTED_PRECOMMIT')
        else:
            raise Error('E_INTEGRITY')
        require(self.counts(p) == before)
        wire = self.workspace / 'private-incident.json'
        wire.write_bytes(canonical({'schema': self.schema, 'root': str(self.root), 'access': self.admin,
                                   'project': p, 'expectedCounts': before, 'mode': 'incident'}))
        self.app.close()
        proc = subprocess.run([sys.executable, '-B', '-m', 'spikes.p4d_g1.replay_process', str(wire)],
                              capture_output=True, timeout=25, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        require(proc.returncode == 0, 'E_INTEGRITY')
        # Reopen only for ordinary shutdown; no recovery/repair is attempted.
        self.app = Application(self.schema, self.root)
        self.passed('C13', childExit=proc.returncode, precommitRollbackNoRows=True,
                    retainedIntakes=1, rolledBackRunEventAndStartReceipt=True,
                    reopenReadDenied='E_UNRESOLVED', schemaRetainedAsIncident=True, automaticRepair=False)
        return {'schema': self.schema, 'namespace': 'g1_', 'transport': 'trusted-local-application-dispatch',
                'providerProof': False, 'qaOrReasoningExecuted': False}
