"""Synthetic candidate application. Public commands never dispatch arbitrary host methods."""
from contextlib import contextmanager
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
import re
import uuid

from .common import VERSION, MAX_BYTES, OPERATIONS, Error, canonical, digest, exact, identifier, require, sha, strict_json
from .storage import Store, Denied, ALLOWED, Jsonb, token_digest, psycopg
from .publication import prepare

DEFAULT_CONFIG = {'maxQueued': 20, 'maxConcurrent': 2, 'maxAttempts': 2, 'leaseSeconds': 30,
                  'runSeconds': 30, 'enabled': True, 'sourceIds': [], 'outboundProviders': []}
from .contracts import FIELDS, READ_ACTION, safe_run
require(set(FIELDS) == set(OPERATIONS), 'E_DEPENDENCY')

def valid_config(config):
    exact(config, 'maxQueued maxConcurrent maxAttempts leaseSeconds runSeconds enabled sourceIds outboundProviders')
    for field, low, high in [('maxQueued', 1, 1000), ('maxConcurrent', 1, 16), ('maxAttempts', 1, 5),
                             ('leaseSeconds', 5, 300), ('runSeconds', 5, 180)]:
        require(type(config[field]) is int and low <= config[field] <= high)
    require(type(config['enabled']) is bool and isinstance(config['sourceIds'], list)
            and len(set(config['sourceIds'])) == len(config['sourceIds']) and config['outboundProviders'] == [])
    for source in config['sourceIds']:
        identifier(source)




class Application:
    def __init__(self, schema, root, *, create=False, observer=None):
        self.observer = observer
        self.store = Store(schema, root, create=create, observer=observer)
        self.conn, self.identity, self.blobs = self.store.conn, self.store.identity, self.store.blobs

    def close(self):
        self.store.close()

    def _notify(self, stage):
        # Trusted fault/observation facility. No request field or public route can supply it.
        if self.observer is not None:
            self.observer(stage)

    def register_snapshot(self, project, snapshot_id, kind, bundle, *, sources, mode='imported', manifest=None):
        """Trusted bootstrap importer only. Not present in HTTP routes or dynamic dispatch."""
        identifier(snapshot_id); require(kind in ('repo_task', 'handoff') and mode in ('imported', 'executed_fixture'))
        require(isinstance(bundle, dict) and len(canonical(bundle)) <= MAX_BYTES)
        runs = bundle.get('runs', [])
        require(len(runs) == 1 and runs[0]['projectId'] == project, 'E_INTEGRITY')
        run = runs[0]
        from qa_core.contracts import validate
        require(not validate(bundle), 'E_INTEGRITY')
        handoff = next(h for h in bundle['handoffs'] if h['id'] == run['handoffId'] and h['projectId'] == project)
        core_target = {'projectId': project, 'runId': run['id'], 'handoffId': run['handoffId'],
                       'taskRef': handoff['taskRef'],
                       'candidateRevision': run['candidateRevision'], 'requirementVersion': handoff['requirementVersion'],
                       'projectConfigVersion': run['projectConfigVersion'], 'dataPolicyVersion': run['dataPolicyVersion']}
        scoped_artifacts = {a['id']: a for a in bundle.get('artifacts', []) if a['projectId'] == project}
        require(scoped_artifacts and set(scoped_artifacts) <= set(sources), 'E_INTEGRITY')
        for aid, artifact in scoped_artifacts.items():
            raw, _, revision = sources[aid]
            require(sha(raw) == artifact['sha256'] and revision == artifact['revision'], 'E_INTEGRITY')
        from .lineage import report_lineage
        projection = report_lineage(bundle, sources)
        reference = self.blobs.put(canonical(bundle))
        data = dict(manifest or {}, mode=mode, run_id=run['id'], sourceIds=sorted(sources),
                    reportSourceIds=projection['sourceIds'], reportProjection=projection, coreTarget=core_target)
        candidate_digest = digest({aid: digest({'bytes': raw.hex(), 'classification': classification, 'revision': revision})
                                   for aid, (raw, classification, revision) in sources.items()})
        with self.store.unit(kind='user', write=True):
            require(self.conn.execute('SELECT 1 FROM rt_projects WHERE project=%s', (project,)).fetchone(), 'E_DENIED')
            for aid, (raw, classification, revision) in sources.items():
                identifier(aid)
                ref = self.blobs.put(raw)
                self.conn.execute('INSERT INTO rt_sources VALUES(%s,%s,%s,%s,%s,%s,%s)',
                                  (project, snapshot_id, aid, Jsonb(ref), classification, revision, Jsonb({'origin': 'registered_operator_bytes'})))
                row = self.conn.execute('SELECT * FROM rt_sources WHERE project=%s AND snapshot=%s AND id=%s', (project, snapshot_id, aid)).fetchone()
                require((row['ref'], row['classification'], row['revision']) == (ref, classification, revision), 'E_CONFLICT')
            self.conn.execute('INSERT INTO rt_snapshots VALUES(%s,%s,%s,%s,%s,%s,%s,%s)',
                              (project, snapshot_id, kind, Jsonb(reference), digest(bundle), candidate_digest, digest(bundle), Jsonb(data)))
        return {'snapshotId': snapshot_id, 'candidateDigest': candidate_digest, 'inputDigest': digest(bundle)}

    def observe_executor(self, project, run_id, effect_nonce, raw_record, job, supervisor):
        """Trusted local executor observation port; absent from all HTTP operation routes.

        The collector process calls this only after actual byte collection and OS/engine
        observation. It does not accept a submitting worker's flags as independent truth.
        Whole-supervisor/pre-identity recovery needs its additional durable safety protocol.
        """
        from spikes.vf1.core_bridge import validate_job
        from spikes.vf1.run_vf1 import build_job, OMITTED
        record = strict_json(raw_record)
        validate_job(job, digest(job))
        with self.store.unit(write=True):
            run = self.store.run(project, run_id)
            snapshot = self.store.snapshot(project, run['snapshot'])
            require(snapshot['manifest']['mode'] == 'executed_fixture' and run['effect_nonce'] == effect_nonce, 'E_INTEGRITY')
            intent = run['effect_witness']['intent']
            owned = run['effect_witness'].get('interruption')
            require(snapshot['manifest']['checkRegistry'] == 'vf1-fixed-1.0.0' and owned is not None
                    and owned['profile'] == 'vf1-fixed-1.0.0' and owned['phase'] == 'qa_completed'
                    and supervisor['unit'] == owned['anchor']['context']['unit']
                    and (supervisor['contextPin'], supervisor['originalJournalPin'], supervisor['finalJournalPin'], supervisor['releasePin']) ==
                    (owned['anchor']['contextPin'], owned['launchPin'], owned['journalPin'], owned['releasePin'])
                    and owned['normalCleanup'] == {'operation': 'qa_success_cleanup',
                        'rawRecordSha256': digest({key: value for key, value in record.items() if key != 'ingestionIntervention'})}, 'E_INTEGRITY')
            require(record['runId'] == job['runId'] == run_id and record['jobId'] == job['jobId'] == intent['jobId']
                    and record['inputHashes'] == intent['inputHashes'] and record['status'] == 'complete', 'E_INTEGRITY')
            require(sha(raw_record) == job['executionSha256'] and record['cleanup'] ==
                    {'containerRemoved': True, 'processesNotLive': True, 'cgroupEmpty': True}, 'E_INTEGRITY')
            require(supervisor['workerExitCode'] == 0 and supervisor['loadState'] == 'not-found' and supervisor['cgroupAbsent'] is True, 'E_UNRESOLVED')
            execution = record['execution']
            require(execution['exitCode'] == 0 and execution['containerStoppedPidZero'] is True
                    and re.fullmatch('[a-f0-9]{64}', execution['containerId']) and execution['processesBefore']
                    and execution['containerCgroup'].startswith('/sys/fs/cgroup/system.slice/' + supervisor['unit'] + '/'), 'E_INTEGRITY')
            withheld = record['ingestionIntervention']['withheldTestIds']
            require(withheld in ([], [OMITTED]) and record['ingestionIntervention']['appliedBeforeHostRequest'] is True, 'E_INTEGRITY')
            payloads = {'case/' + item['relativePath']: item['text'].encode('utf-8') for item in job['artifacts']}
            require(build_job(record, sha(raw_record), withheld, payloads) == job, 'E_INTEGRITY')
            require({a['relativePath']: a['sha256'] for a in job['artifacts']} == snapshot['manifest']['artifactHashes'], 'E_INTEGRITY')
            raw_ref = self.blobs.put(raw_record)
            identity = {key: execution[key] for key in ('containerId', 'containerName', 'containerCgroup', 'processesBefore', 'labels')}
            require(owned['resource']['containerId'] == identity['containerId']
                    and owned['resource']['cgroup'] == identity['containerCgroup'], 'E_INTEGRITY')
            cleanup = dict(record['cleanup'], resourceIdentity=identity)
            accepted_execution = {'mode': 'executed_fixture', 'inputDigest': snapshot['input_digest'], 'job': job,
                                  'recordSha256': sha(raw_record)}
            observation = {'rawRef': raw_ref, 'jobRef': self.blobs.put(canonical(job)),
                           'execution': accepted_execution, 'cleanup': cleanup, 'supervisor': supervisor}
            previous = run['effect_witness'].get('observation')
            require(previous is None or previous == observation, 'E_CONFLICT')
            self.conn.execute('UPDATE rt_runs SET effect_witness=%s WHERE project=%s AND id=%s',
                              (Jsonb(dict(run['effect_witness'], intent=intent, observation=observation)), project, run_id))
        return {'execution': accepted_execution, 'cleanup': cleanup}

    def source_record(self, run, artifact_id):
        """Resolve static input or exact private executor derivative; no arbitrary paths."""
        row = self.conn.execute('SELECT * FROM rt_sources WHERE project=%s AND snapshot=%s AND id=%s',
                                (run['project'], run['snapshot'], artifact_id)).fetchone()
        if row is not None:
            return row
        observation = (run.get('effect_witness') or {}).get('observation')
        require(observation is not None and artifact_id in ('vf1-execution-record', 'vf1-coverage-policy'), 'E_DENIED')
        ref = observation['rawRef'] if artifact_id == 'vf1-execution-record' else observation['jobRef']
        snapshot = self.store.snapshot(run['project'], run['snapshot'])
        return {'id': artifact_id, 'classification': 'restricted', 'ref': ref,
                'revision': snapshot['manifest']['coreTarget']['candidateRevision'] if artifact_id == 'vf1-execution-record' else 'vf1-job-1.0.0'}

    def dispatch(self, operation, token, body):
        try:
            require(operation in FIELDS)
            require(isinstance(body, dict) and len(canonical(body)) <= MAX_BYTES)
            require(body.get('version') == VERSION, 'E_VERSION')
            params = dict(body); del params['version']; exact(params, FIELDS[operation])
            for field in ('expected_config', 'expected_version', 'expected_run_version', 'fence', 'after'):
                if field in params:
                    require(type(params[field]) is int and params[field] >= (0 if field == 'after' else 1))
            # Fixed handler partition, never method names obtained from artifact content.
            if operation in READ_ACTION:
                return self._read(operation, token, params)
            if operation.startswith('session_') or operation.startswith('account_'):
                return self._identity(operation, token, params)
            if operation in ('project_create', 'project_configure', 'grant_issue', 'grant_revoke', 'service_enroll', 'service_revoke'):
                return self._management(operation, token, params)
            if operation in ('intake_snapshot', 'run_start', 'run_cancel'):
                return self._command(operation, token, params)
            result = self._worker(operation, token, params)
            if operation == 'worker_submit':
                self._notify('publication_committed')
            elif operation == 'worker_claim':
                self._notify('claim_committed')
            return result
        except Error:
            raise
        except Denied as exc:
            raise Error(exc.code if exc.code in ('E_AUTH', 'E_DENIED', 'E_STALE', 'E_CONFLICT') else 'E_AUTH') from None
        except psycopg.Error:
            raise Error('E_DEPENDENCY') from None
        except (KeyError, TypeError, ValueError, OSError):
            raise Error('E_INPUT') from None

    def _identity(self, op, token, p):
        if op in ('session_login', 'session_refresh'):
            failure = None; result = None
            with self.store.unit(write=True):
                try:
                    result = (self.identity.login(p['user'], p['password'], access_ms=900000, refresh_ms=1800000)
                              if op == 'session_login' else self.identity.refresh(p['refresh'], access_ms=900000, refresh_ms=1800000))
                except Denied as exc:
                    failure = exc
            if failure:
                raise Error('E_AUTH')
            return dict(result, version=VERSION)
        with self.store.unit(token, write=True, restricted=op in ('session_logout', 'session_change_password')) as (actor, _):
            if op == 'session_logout':
                self.identity.logout(token)
            elif op == 'session_change_password':
                self.identity.change_password(token, p['old'], p['new'])
            elif op == 'account_create':
                self.identity.create_account(token, p['user'], p['password'])
            elif op == 'account_set_enabled':
                self.identity.account_flag(token, p['user'], 'enabled', p['enabled'])
            elif op == 'account_set_role':
                self.identity.membership(token, p['project'], p['user'], p['role'])
            elif op == 'account_reset_password':
                self.identity.reset_password(token, p['user'], p['password'])
            else:
                raise Error('E_INPUT')
        return {'accepted': True}

    def _management(self, op, token, p):
        with self.store.unit(token, write=True) as (actor, deadlines):
            if op == 'project_create':
                self.identity.create_project(token, p['project'], p['owner'])
                self.conn.execute('INSERT INTO rt_projects VALUES(%s,1,1,true)', (p['project'],))
                self.conn.execute('INSERT INTO rt_configs VALUES(%s,1,1,%s)', (p['project'], Jsonb(DEFAULT_CONFIG)))
                return {'project': p['project'], 'configVersion': 1, 'policyVersion': 1}
            if op == 'service_enroll':
                self.identity.admin(actor); identifier(p['service'])
                require(p['kind'] in ('scheduler', 'worker', 'collector', 'assessor') and isinstance(p['projects'], list)
                        and p['projects'] and len(p['projects']) == len(set(p['projects'])))
                for project in p['projects']:
                    self.identity.role(actor, project)
                self.conn.execute('INSERT INTO rt_services(id,kind,epoch,projects) VALUES(%s,%s,1,%s)',
                                  (p['service'], p['kind'], Jsonb(p['projects'])))
                credential = self.store.issue_token('s')
                self.conn.execute("INSERT INTO rt_credentials VALUES(%s,%s,1,clock_timestamp()+interval '30 minutes')",
                                  (token_digest(credential, 's'), p['service']))
                return {'service': p['service'], 'kind': p['kind'], 'credential': credential}
            if op == 'service_revoke':
                self.identity.admin(actor)
                require(self.conn.execute('UPDATE rt_services SET enabled=false,epoch=epoch+1 WHERE id=%s RETURNING id', (p['service'],)).fetchone(), 'E_DENIED')
                return {'revoked': True}
            if op == 'project_configure':
                config, _ = self.store.config(actor, p['project'], 'config', allow_disabled=True); valid_config(p['config'])
                require(config['config_version'] == p['expected_config'], 'E_STALE')
                for source in p['config']['sourceIds']:
                    require(self.conn.execute('SELECT 1 FROM rt_sources WHERE project=%s AND id=%s', (p['project'], source)).fetchone(), 'E_DENIED')
                version, policy = config['config_version'] + 1, config['policy_version'] + 1
                self.conn.execute('INSERT INTO rt_configs VALUES(%s,%s,%s,%s)', (p['project'], version, policy, Jsonb(p['config'])))
                self.conn.execute('UPDATE rt_projects SET config_version=%s,policy_version=%s WHERE project=%s', (version, policy, p['project']))
                return {'configVersion': version, 'policyVersion': policy}
            config, role = self.store.config(actor, p['project'])
            if op == 'grant_issue':
                require(config['config_version'] == p['expected_config'], 'E_STALE')
                actions = p['actions']
                require(isinstance(actions, list) and actions and all(isinstance(a, str) for a in actions)
                        and len(actions) == len(set(actions)) and set(actions) <= ALLOWED[role], 'E_DENIED')
                grant = uuid.uuid4().hex
                row = self.conn.execute('''INSERT INTO rt_grants VALUES(%s,%s,%s,%s,%s,%s,%s,
                    clock_timestamp()+interval '30 minutes',false) RETURNING expires''',
                    (grant, p['project'], actor['id'], actor['epoch'], config['config_version'], config['policy_version'], Jsonb(actions))).fetchone()
                return {'grant': grant, 'expiresAt': row['expires'].isoformat()}
            row = self.conn.execute('SELECT * FROM rt_grants WHERE id=%s AND project=%s', (p['grant'], p['project'])).fetchone()
            require(row is not None and (row['user_id'] == actor['id'] or role in ('Owner', 'Admin')), 'E_DENIED')
            self.conn.execute('UPDATE rt_grants SET revoked=true WHERE id=%s', (p['grant'],))
            return {'revoked': True}

    def _command(self, op, token, p):
        with self.store.unit(token, write=True) as (actor, deadlines):
            if op == 'intake_snapshot':
                config, _ = self.store.config(actor, p['project'], 'start')
                require(config['config_version'] == p['expected_config'], 'E_STALE')
                previous = self.store.prior(actor, p['project'], op, p['key'], p)
                snapshot = self.store.snapshot(p['project'], p['snapshot_ref'])
                require(snapshot['kind'] == p['kind'] and snapshot['candidate_digest'] == p['candidate_digest']
                        and snapshot['input_digest'] == p['input_digest'], 'E_INTEGRITY')
                self.store.source_scope(snapshot, config)
                if previous is not None:
                    return previous
                intake = 'intake_' + uuid.uuid4().hex
                self.conn.execute('INSERT INTO rt_intakes VALUES(%s,%s,%s,%s,%s)',
                                  (p['project'], intake, snapshot['id'], p['kind'], actor['id']))
                result = {'intakeId': intake, 'candidateDigest': snapshot['candidate_digest'], 'inputDigest': snapshot['input_digest']}
            else:
                action = 'start' if op == 'run_start' else 'cancel'
                config, role, grant = self.store.grant(actor, p['project'], p['grant'], action, deadlines)
                previous = self.store.prior(actor, p['project'], op, p['key'], p)
                if previous is not None:
                    self.store.config(actor, p['project'], 'read')
                    if op == 'run_start':
                        prior_run = self.store.run(p['project'], p['run_id'])
                        self.store.source_scope(self.store.snapshot(p['project'], prior_run['snapshot']), config)
                    return previous
                if op == 'run_start':
                    identifier(p['run_id'])
                    require(config['config_version'] == p['expected_config'], 'E_STALE')
                    intake = self.conn.execute('SELECT * FROM rt_intakes WHERE project=%s AND id=%s AND actor=%s',
                                               (p['project'], p['intake_id'], actor['id'])).fetchone()
                    require(intake is not None, 'E_DENIED')
                    snapshot = self.store.snapshot(p['project'], intake['snapshot'])
                    self.store.source_scope(snapshot, config)
                    require(snapshot['manifest']['run_id'] == p['run_id'], 'E_INTEGRITY')
                    target = snapshot['manifest']['coreTarget']
                    require(target['projectConfigVersion'] == config['config_version'] and target['dataPolicyVersion'] == config['policy_version'], 'E_STALE')
                    count = self.conn.execute("SELECT count(*) AS n FROM rt_runs WHERE project=%s AND state='queued'", (p['project'],)).fetchone()['n']
                    require(count < config['payload']['maxQueued'], 'E_BUDGET')
                    require(not self.conn.execute('SELECT 1 FROM rt_runs WHERE project=%s AND id=%s', (p['project'], p['run_id'])).fetchone(), 'E_CONFLICT')
                    self.conn.execute('''INSERT INTO rt_runs(project,id,snapshot,owner,grant_id,user_epoch,config_version,policy_version,state)
                        VALUES(%s,%s,%s,%s,%s,%s,%s,%s,'queued')''',
                        (p['project'], p['run_id'], snapshot['id'], actor['id'], p['grant'], actor['epoch'], config['config_version'], config['policy_version']))
                    run = self.store.run(p['project'], p['run_id']); self.store.event(run, 'run_state', {'state': 'queued'})
                    result = dict(safe_run(self.store.run(p['project'], p['run_id'])), accepted=True)
                else:
                    run = self.store.run(p['project'], p['run_id'])
                    require(role != 'Runner' or run['owner'] == actor['id'], 'E_DENIED')
                    require(run['version'] == p['expected_version'] and run['state'] not in ('completed', 'failed', 'cancelled'), 'E_STALE')
                    proof = self.conn.execute('SELECT * FROM rt_executions WHERE project=%s AND run_id=%s AND assignment=%s',
                                              (p['project'], p['run_id'], run['assignment'])).fetchone() if run['assignment'] else None
                    safe = run['effect_nonce'] is None or (proof is not None and proof['fence'] == run['fence']
                           and proof['effect_nonce'] == run['effect_nonce'] and self._cleanup_valid(proof['cleanup'],
                           self.store.snapshot(p['project'], run['snapshot'])))
                    state = 'cancelled' if safe else 'stopping'
                    self.conn.execute('''UPDATE rt_runs SET state=%s,version=version+1,cancel_requested=true,
                        incident=%s WHERE project=%s AND id=%s''', (state, not safe, p['project'], p['run_id']))
                    self.store.event(run, 'run_state', {'state': state})
                    result = dict(safe_run(self.store.run(p['project'], p['run_id'])), accepted=True)
            self.store.save_receipt(actor, p['project'], op, p['key'], p, result)
            return result

    def _read(self, op, token, p):
        with self.store.unit(token) as (actor, _):
            return self._read_locked(op, actor, p)

    def _read_locked(self, op, actor, p):
        from .readside import read_locked
        return read_locked(self, op, actor, p)

    @contextmanager
    def release_unit(self, operation, token, body, result):
        from .readside import release_unit
        try:
            with release_unit(self, operation, token, body, result):
                yield
        except Denied as exc:
            raise Error('E_DENIED' if exc.code == 'E_DENIED' else 'E_AUTH') from None
        except psycopg.Error:
            raise Error('E_DEPENDENCY') from None

    def _worker(self, op, token, p):
        kind = 'scheduler' if op in ('worker_claim', 'worker_recover_claim') else 'collector' if op == 'collector_record' else 'assessor' if op == 'assessment_accept' else 'worker'
        with self.store.unit(token, kind=kind, project=p['project'], write=True) as (actor, deadlines):
            run = self.store.run(p['project'], p['run_id'])
            snapshot = self.store.snapshot(p['project'], run['snapshot'])
            if op == 'worker_recover_claim':
                require(run['assignment'] is not None and (run['claim_scheduler'], run['claim_scheduler_epoch'],
                        run['claim_expected_version'], run['worker']) ==
                        (actor['id'], actor['epoch'], p['expected_run_version'], p['worker']), 'E_DENIED')
                if run['state'] in ('completed', 'cancelled', 'failed'):
                    return safe_run(run)
                require(run['state'] == 'collecting' and run['effect_nonce'] is None and not run['incident'], 'E_UNRESOLVED')
                work_deadlines = list(deadlines)
                try:
                    self.store.current_work(run, work_deadlines)
                except (Denied, Error):
                    # No consumed effect exists: fencing the delivery and closing processing
                    # requires no invented execution or resource-cleanup acknowledgement.
                    self.conn.execute("""UPDATE rt_runs SET state='failed',fence=fence+1,lease_hash=NULL,
                        lease_expires=NULL,version=version+1,effect_state='not_admitted'
                        WHERE project=%s AND id=%s""", (p['project'], p['run_id']))
                    self.store.event(run, 'run_state', {'state': 'failed', 'reason': 'claim_authority_expired_before_effect'})
                    return safe_run(self.store.run(p['project'], p['run_id']))
                require(run['delivery_count'] < 4, 'E_BUDGET')
                deadlines[:] = work_deadlines
                lease = self.store.issue_token('l')
                row = self.conn.execute('''UPDATE rt_runs SET fence=fence+1,lease_hash=%s,delivery_count=delivery_count+1
                    WHERE project=%s AND id=%s RETURNING *''', (token_digest(lease, 'l'), p['project'], p['run_id'])).fetchone()
                return self._claim_view(row, snapshot, lease)
            if op == 'worker_claim':
                config = self.store.delegation(run, deadlines)
                require(run['state'] == 'queued' and run['version'] == p['expected_run_version'] and not run['incident'], 'E_STALE')
                require(run['attempt'] < config['payload']['maxAttempts'], 'E_BUDGET')
                counts = self.conn.execute("SELECT count(*) AS all_count,count(*) FILTER(WHERE project=%s) AS project_count FROM rt_runs WHERE assignment IS NOT NULL AND state NOT IN('completed','cancelled','failed')", (p['project'],)).fetchone()
                require(counts['all_count'] < 16 and counts['project_count'] < config['payload']['maxConcurrent'], 'E_BUDGET')
                worker = self.conn.execute("SELECT * FROM rt_services WHERE id=%s AND kind='worker' AND enabled", (p['worker'],)).fetchone()
                require(worker is not None and p['project'] in worker['projects'], 'E_DENIED')
                assignment, lease = uuid.uuid4().hex, self.store.issue_token('l')
                row = self.conn.execute('''UPDATE rt_runs SET assignment=%s,worker=%s,worker_epoch=%s,attempt=attempt+1,
                    fence=fence+1,lease_hash=%s,run_deadline=clock_timestamp()+(%s*interval '1 second'),
                    lease_expires=LEAST(%s,clock_timestamp()+(%s*interval '1 second'),
                    clock_timestamp()+(%s*interval '1 second')),state='collecting',version=version+1,
                    claim_scheduler=%s,claim_scheduler_epoch=%s,claim_expected_version=%s,delivery_count=1
                    WHERE project=%s AND id=%s RETURNING *''', (assignment, worker['id'], worker['epoch'], token_digest(lease, 'l'),
                    config['payload']['runSeconds'], min(deadlines), config['payload']['leaseSeconds'],
                    config['payload']['runSeconds'], actor['id'], actor['epoch'], p['expected_run_version'], p['project'], p['run_id'])).fetchone()
                self.store.event(row, 'run_state', {'state': 'collecting'})
                return self._claim_view(row, snapshot, lease)
            if kind in ('collector', 'assessor'):
                require((run['assignment'], run['fence'], run['effect_nonce']) == (p['assignment'], p['fence'], p['effect_nonce'])
                        and run['effect_nonce'] is not None, 'E_STALE')
                if kind == 'collector':
                    previous = self.conn.execute('SELECT * FROM rt_executions WHERE project=%s AND run_id=%s AND assignment=%s',
                        (p['project'], p['run_id'], run['assignment'])).fetchone()
                    if previous:
                        require((previous['record_digest'], previous['cleanup']) == (digest(p['execution']), p['cleanup']), 'E_CONFLICT')
                        return {'executionDigest': previous['record_digest'], 'accepted': previous['work_accepted'],
                                'cleanupOnly': not previous['work_accepted']}
                    require(run['state'] in ('collecting', 'stopping', 'unresolved'), 'E_STALE')
                    candidate_deadlines = list(deadlines)
                    try:
                        self.store.current_work(run, candidate_deadlines)
                    except (Error, Denied):
                        # Cleanup reduces authority. Never revive work after cancellation/expiry/revoke.
                        return self._collect_or_assess(op, actor, p, run, snapshot, cleanup_only=True)
                    deadlines[:] = candidate_deadlines
                else:
                    require(run['state'] in ('awaiting_assessment', 'analyzing'), 'E_STALE')
                    self.store.current_work(run, deadlines)
                return self._collect_or_assess(op, actor, p, run, snapshot)
            if op == 'worker_submit' and run['state'] == 'completed':
                self.store.assignment(actor, p, deadlines, live=False)
                report = self.conn.execute('SELECT * FROM rt_reports WHERE project=%s AND run_id=%s', (p['project'], p['run_id'])).fetchone()
                require(report is not None and report['assessment_digest'] == p['assessment_digest'], 'E_CONFLICT')
                return dict(safe_run(run), reportId=report['report_id'])
            run = self.store.assignment(actor, p, deadlines, live=op != 'worker_observe_cleanup')
            if op == 'worker_renew':
                config = self.store.delegation(run, deadlines)
                limits = [run['run_deadline'], self.conn.execute('SELECT expires FROM rt_grants WHERE id=%s',
                          (run['grant_id'],)).fetchone()['expires'], actor['expires']]
                row = self.conn.execute('''UPDATE rt_runs SET lease_expires=LEAST(%s,clock_timestamp()+(%s*interval '1 second'))
                    WHERE project=%s AND id=%s RETURNING lease_expires''', (min(limits), config['payload']['leaseSeconds'], p['project'], p['run_id'])).fetchone()
                return {'leaseExpiresAt': row['lease_expires'].isoformat()}
            if op == 'worker_admit':
                require(run['state'] == 'collecting' and run['effect_nonce'] is None and not run['incident'], 'E_CONFLICT')
                effect = uuid.uuid4().hex
                intent = {'jobId': 'job-' + effect[:16], 'inputHashes': snapshot['manifest'].get('inputHashes', {}),
                          'snapshotId': snapshot['id'], 'effectNonce': effect, 'assignment': run['assignment'], 'fence': run['fence']}
                self.conn.execute("UPDATE rt_runs SET effect_nonce=%s,effect_witness=%s,effect_state='consumed',incident=true,version=version+1 WHERE project=%s AND id=%s",
                                  (effect, Jsonb({'intent': intent}), p['project'], p['run_id']))
                return {'accepted': True, 'state': 'collecting', 'runId': run['id'], 'stateVersion': run['version'] + 1,
                        'effectNonce': effect, 'jobId': intent['jobId'], 'snapshotId': snapshot['id'], 'manifest': snapshot['manifest']}
            if op == 'worker_observe_cleanup':
                proof = self.conn.execute('SELECT * FROM rt_executions WHERE project=%s AND run_id=%s AND assignment=%s',
                                          (p['project'], p['run_id'], run['assignment'])).fetchone()
                require(proof is not None and self._cleanup_valid(proof['cleanup'], snapshot), 'E_UNRESOLVED')
                state = 'cancelled' if run['cancel_requested'] else 'failed'
                require(run['state'] in ('stopping', 'unresolved'), 'E_STALE')
                self.conn.execute('UPDATE rt_runs SET state=%s,incident=false,version=version+1 WHERE project=%s AND id=%s', (state, p['project'], p['run_id']))
                self.store.event(run, 'run_state', {'state': state})
                return safe_run(self.store.run(p['project'], p['run_id']))
            if op == 'worker_fail':
                require(p['code'] in ('check_error', 'assessment_missing', 'cleanup_unconfirmed', 'deadline_exceeded'))
                self.conn.execute("UPDATE rt_runs SET state='unresolved',incident=true,version=version+1 WHERE project=%s AND id=%s", (p['project'], p['run_id']))
                self.store.event(run, 'run_state', {'state': 'unresolved'})
                return safe_run(self.store.run(p['project'], p['run_id']))
            return self._publish(p, run, snapshot)

    @staticmethod
    def _claim_view(run, snapshot, lease):
        return {'runId': run['id'], 'project': run['project'], 'assignment': run['assignment'], 'fence': run['fence'],
                'lease_token': lease, 'leaseExpiresAt': run['lease_expires'].isoformat(), 'snapshotId': snapshot['id'],
                'candidateDigest': snapshot['candidate_digest'], 'inputDigest': snapshot['input_digest'],
                'configVersion': run['config_version'], 'policyVersion': run['policy_version']}

    @staticmethod
    def _cleanup_valid(cleanup, snapshot):
        if snapshot['manifest']['mode'] == 'imported':
            return cleanup == {'noExecutionRequired': True, 'mode': 'imported'}
        return (isinstance(cleanup, dict) and all(cleanup.get(k) is True for k in
                ('containerRemoved', 'processesNotLive', 'cgroupEmpty')) and
                isinstance(cleanup.get('resourceIdentity'), dict))

    def _collect_or_assess(self, op, actor, p, run, snapshot, *, cleanup_only=False):
        if op == 'collector_record':
            execution = p['execution']; require(isinstance(execution, dict), 'E_INTEGRITY')
            require(execution.get('mode') == snapshot['manifest']['mode'] and execution.get('inputDigest') == snapshot['input_digest'], 'E_INTEGRITY')
            require(self._cleanup_valid(p['cleanup'], snapshot), 'E_UNRESOLVED')
            if snapshot['manifest']['mode'] == 'executed_fixture':
                witness = (run['effect_witness'] or {}).get('observation')
                require(witness is not None and execution == witness['execution'] and p['cleanup'] == witness['cleanup'], 'E_UNRESOLVED')
                require(sha(self.blobs.get(witness['rawRef'])) == execution['recordSha256'], 'E_INTEGRITY')
            record_ref = self.blobs.put(canonical(execution))
            previous = self.conn.execute('SELECT * FROM rt_executions WHERE project=%s AND run_id=%s AND assignment=%s', (p['project'], p['run_id'], run['assignment'])).fetchone()
            if previous:
                require((previous['record_digest'], previous['cleanup']) == (digest(execution), p['cleanup']), 'E_CONFLICT')
            else:
                self.conn.execute('INSERT INTO rt_executions VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                                  (p['project'], p['run_id'], run['assignment'], run['fence'], run['effect_nonce'], Jsonb(record_ref), digest(execution), Jsonb(p['cleanup']), actor['id'], not cleanup_only))
                state = ('cancelled' if run['cancel_requested'] else 'failed') if cleanup_only else 'awaiting_assessment'
                self.conn.execute("UPDATE rt_runs SET state=%s,incident=false,version=version+1 WHERE project=%s AND id=%s", (state, p['project'], p['run_id']))
                self.store.event(run, 'run_state' if cleanup_only else 'check_completed', {'state': state, 'evidenceMode': execution['mode']})
            return {'executionDigest': digest(execution), 'accepted': not cleanup_only, 'cleanupOnly': cleanup_only}
        evidence = self.conn.execute('SELECT * FROM rt_executions WHERE project=%s AND run_id=%s AND assignment=%s', (p['project'], p['run_id'], run['assignment'])).fetchone()
        require(evidence is not None and evidence['work_accepted'] and evidence['record_digest'] == p['execution_digest'], 'E_INTEGRITY')
        require(digest(p['bundle']) == p['bundle_digest'] and digest(p['assessment']) == p['assessment_digest'], 'E_INTEGRITY')
        if snapshot['manifest']['mode'] == 'imported':
            require(p['bundle_digest'] == snapshot['bundle_digest'], 'E_INTEGRITY')
        else:
            from .execution_projection import project as project_execution
            execution = strict_json(self.blobs.get(evidence['record_ref'])); job = execution['job']
            response = {'version': 'vf1-host-response-1.0.0', 'runId': job['runId'], 'jobId': job['jobId'], 'jobDigest': digest(job),
                        **{key: p['assessment'][key] for key in ('risk', 'criteria', 'evidenceReviews', 'bindings')}}
            projected = project_execution(job, response, snapshot['manifest']['coreTarget'])
            require(projected['assessment'] == p['assessment'] and projected['bundle'] == p['bundle'], 'E_INTEGRITY')
        prepared = prepare(p['bundle'], p['assessment'], expected_bundle_digest=p['bundle_digest'],
                           expected_assessment_digest=p['assessment_digest'], run_id=run['id'], report_id='report_' + run['id'])
        self._held_target(prepared, run, snapshot)
        bundle_ref, assessment_ref = self.blobs.put(canonical(p['bundle'])), self.blobs.put(canonical(p['assessment']))
        existing = self.conn.execute('SELECT * FROM rt_assessments WHERE project=%s AND run_id=%s AND assignment=%s', (p['project'], p['run_id'], run['assignment'])).fetchone()
        if existing:
            require((existing['bundle_digest'], existing['assessment_digest']) == (p['bundle_digest'], p['assessment_digest']), 'E_CONFLICT')
        else:
            self.conn.execute('INSERT INTO rt_assessments VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                              (p['project'], p['run_id'], run['assignment'], run['fence'], Jsonb(bundle_ref), Jsonb(assessment_ref),
                               p['bundle_digest'], p['assessment_digest'], p['execution_digest'], actor['id']))
            self.conn.execute("UPDATE rt_runs SET state='analyzing',version=version+1 WHERE project=%s AND id=%s", (p['project'], p['run_id']))
            self.store.event(run, 'run_state', {'state': 'analyzing'})
        return {'accepted': True, 'assessmentDigest': p['assessment_digest']}

    @staticmethod
    def _held_target(prepared, run, snapshot):
        target = prepared.package['target']
        held = dict(snapshot['manifest']['coreTarget'], projectId=run['project'], runId=run['id'],
                    projectConfigVersion=run['config_version'], dataPolicyVersion=run['policy_version'])
        require(all(target[key] == value for key, value in held.items()), 'E_INTEGRITY')

    def _publish(self, p, run, snapshot):
        assessment = self.conn.execute('SELECT * FROM rt_assessments WHERE project=%s AND run_id=%s AND assignment=%s', (p['project'], p['run_id'], run['assignment'])).fetchone()
        evidence = self.conn.execute('SELECT * FROM rt_executions WHERE project=%s AND run_id=%s AND assignment=%s', (p['project'], p['run_id'], run['assignment'])).fetchone()
        require(assessment is not None and assessment['assessment_digest'] == p['assessment_digest'] and evidence is not None
                and self._cleanup_valid(evidence['cleanup'], snapshot) and not run['incident'], 'E_UNRESOLVED')
        bundle, assessed = strict_json(self.blobs.get(assessment['bundle_ref'])), strict_json(self.blobs.get(assessment['assessment_ref']))
        report_id = 'report_' + run['id']
        prepared = prepare(bundle, assessed, expected_bundle_digest=assessment['bundle_digest'], expected_assessment_digest=assessment['assessment_digest'],
                           run_id=run['id'], report_id=report_id)
        self._held_target(prepared, run, snapshot)
        # Actual immutable bytes are durable before the authoritative reference/outbox transaction commits.
        self._notify('publication_stage_begin')
        private_ref, view_ref = self.blobs.put(prepared.private_bytes), self.blobs.put(prepared.view_bytes)
        self.blobs.get(private_ref); self.blobs.get(view_ref)
        self._notify('publication_staged')
        from .lineage import report_lineage
        source_bytes = {}
        for artifact in bundle['artifacts']:
            if artifact['projectId'] == run['project']:
                source = self.source_record(run, artifact['id'])
                raw = self.blobs.get(source['ref'])
                require(sha(raw) == artifact['sha256'] and source['revision'] == artifact['revision'], 'E_INTEGRITY')
                source_bytes[artifact['id']] = (raw, source['classification'], source['revision'])
        projection = report_lineage(bundle, source_bytes)
        require(projection['sourceIds'] == snapshot['manifest']['reportSourceIds'], 'E_INTEGRITY')
        self.conn.execute('INSERT INTO rt_reports VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                          (p['project'], p['run_id'], report_id, Jsonb(private_ref), Jsonb(view_ref), Jsonb(prepared.lineage),
                           Jsonb(projection), assessment['bundle_digest'], assessment['assessment_digest']))
        self.conn.execute("UPDATE rt_runs SET state='completed',version=version+1,lease_expires=NULL,effect_state='cleaned' WHERE project=%s AND id=%s", (p['project'], p['run_id']))
        self.store.event(run, 'report_ready', {'reportId': report_id, 'state': 'completed', 'humanDecision': 'pending'})
        self._notify('publication_uncommitted')
        return dict(safe_run(self.store.run(p['project'], p['run_id'])), reportId=report_id)
