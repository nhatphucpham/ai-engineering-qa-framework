"""Private operator controller for the bounded M50 interruption profile."""
from dataclasses import dataclass, replace
import re

from runtime_candidate.common import Error, canonical, digest, require, sha, strict_json
from runtime_candidate.storage import Denied, Jsonb, token_digest


PROFILE = 'm50-controlled-interruption-1.0.0'
QA_PROFILE = 'vf1-fixed-1.0.0'
WINDOWS = frozenset(('before_create', 'after_start', 'after_identity'))


def journal_pin(binding, context_pin, *, epoch=0, phase='consumed', resource=None, proof=None):
    state = {'binding': binding, 'contextPin': context_pin, 'epoch': epoch, 'phase': phase, 'resource': resource}
    if proof is not None:
        state['proof'] = proof
    return digest(state)


def unit_anchor(unit):
    ctx = unit.ready['context']
    anchor = {'context': ctx, 'contextPin': unit.ready['contextPin']}
    require(digest(ctx) == anchor['contextPin'] and ctx['version'] == 's4f-context-v3', 'E_CONTEXT')
    return anchor


@dataclass(frozen=True)
class Resource:
    binding: dict
    anchor: dict
    pin: str
    observed: dict | None
    window: str | None = None

    @property
    def profile(self):
        return self.anchor['context'].get('profile', PROFILE)


@dataclass(frozen=True)
class Recovery:
    resource: Resource
    current_fence: int
    run_version: int
    epoch: int = 1


def collection_body(recovery, pair):
    b = recovery.resource.binding
    return dict(project=b['project'], run_id=b['run_id'], assignment=b['assignment_id'],
                fence=recovery.current_fence, effect_nonce=b['effectNonce'], **pair)


class Controller:
    def __init__(self, app):
        self.app = app
        self.store = app.store
        self.conn = app.conn
        self.last_resource = None
        self.last_recovery = None
        self.last_cleanup = None

    def _write(self, run, witness):
        row = self.conn.execute('''UPDATE rt_runs SET effect_witness=%s WHERE project=%s AND id=%s
            AND version=%s AND fence=%s AND assignment=%s AND effect_nonce=%s RETURNING id''',
            (Jsonb(witness), run['project'], run['id'], run['version'], run['fence'],
             run['assignment'], run['effect_nonce'])).fetchone()
        require(row is not None, 'E_STALE')

    def _intent(self, run, *, profile=None):
        snapshot = self.store.snapshot(run['project'], run['snapshot'])
        manifest = snapshot['manifest']
        registered = manifest['checkRegistry']
        require(manifest['mode'] == 'executed_fixture' and registered in (PROFILE, QA_PROFILE)
                and (profile is None or profile == registered), 'E_PROFILE')
        witness = run['effect_witness']
        intent = witness['intent']
        require(run['effect_nonce'] and intent['effectNonce'] == run['effect_nonce']
                and intent['snapshotId'] == run['snapshot'] == snapshot['id']
                and intent['inputHashes'] == manifest['inputHashes'], 'E_BINDING')
        if registered == PROFILE:
            require(intent['inputHashes'] == {}, 'E_PROFILE')
        return snapshot, witness, intent

    def _original(self, body, actor, deadlines, admission, original):
        run = self.store.assignment(actor, body, deadlines)
        snapshot, witness, intent = self._intent(run)
        require(run['state'] == 'collecting' and run['incident'] and run['effect_state'] == 'consumed'
                and (intent['assignment'], intent['fence']) == (run['assignment'], run['fence'])
                and (admission['effectNonce'], admission['jobId'], admission['snapshotId']) ==
                    (run['effect_nonce'], intent['jobId'], run['snapshot']), 'E_BINDING')
        require('observation' not in witness, 'E_ONE_USE')
        anchor = unit_anchor(original)
        ctx = anchor['context']
        require(original.name == ctx['unit'] and original.ready['process'] == ctx['supervisor']
                and original.process.poll() is None, 'E_UNIT_IDENTITY')
        profile = ctx.get('profile', PROFILE)
        require(profile == snapshot['manifest']['checkRegistry'], 'E_PROFILE')
        if profile == QA_PROFILE:
            require((ctx['admissionRunId'], ctx['admissionJobId'], ctx['heldInputPinsSha256']) ==
                    (run['id'], intent['jobId'], digest(intent['inputHashes'])), 'E_BINDING')
        effect = run['effect_nonce']
        require(re.fullmatch('[a-f0-9]{32}', effect), 'E_BINDING')
        binding = {'job': effect, 'effectNonce': effect, 'project': run['project'], 'run_id': run['id'],
                   'assignment_id': run['assignment'], 'attempt': run['attempt'], 'fence': run['fence'],
                   'generation': ctx['generation'], 'container_name': 'qa-s4-f-' + effect}
        return run, witness, intent, binding, anchor

    def arm(self, worker_token, body, admission, original):
        with self.store.unit(worker_token, kind='worker', project=body['project'], write=True) as (actor, deadlines):
            run, witness, intent, b, anchor = self._original(body, actor, deadlines, admission, original)
            require('interruption' not in witness, 'E_ONE_USE')
            reply = original.request('arm', binding=b)
            require(reply == {'journalPin': journal_pin(b, anchor['contextPin'])}, 'E_JOURNAL')
            resource = Resource(b, anchor, reply['journalPin'], None)
            self.last_resource = resource
            owned = {'profile': resource.profile, 'admissionJobId': intent['jobId'], 'binding': b, 'anchor': anchor,
                     'armPin': resource.pin, 'journalPin': resource.pin, 'resource': None, 'phase': 'armed'}
            self._write(run, dict(witness, interruption=owned))
        return resource

    def _bound(self, resource, fence):
        b = resource.binding
        run = self.store.run(b['project'], b['run_id'])
        require((run['assignment'], run['attempt'], run['fence'], run['effect_nonce']) ==
                (b['assignment_id'], b['attempt'], fence, b['effectNonce']), 'E_STALE')
        snapshot, witness, intent = self._intent(run, profile=resource.profile)
        owned = witness['interruption']
        require((owned['profile'], owned['binding'], owned['anchor'], owned['resource'], owned['admissionJobId']) ==
                (resource.profile, b, resource.anchor, resource.observed, intent['jobId'])
                and owned.get('window') == resource.window
                and (intent['assignment'], intent['fence']) == (b['assignment_id'], b['fence']), 'E_BINDING')
        return run, snapshot, witness, owned

    def _authority_loss(self, run, *, worker_token):
        due = self.conn.execute('''WITH observed_clock AS MATERIALIZED (SELECT clock_timestamp() AS observed)
            SELECT observed,%s<=observed AS budget_due,%s<=observed AS lease_due FROM observed_clock''',
            (run['run_deadline'], run['lease_expires'])).fetchone()
        if run['cancel_requested'] and run['state'] == 'stopping':
            reason = 'cancelled_by_user'
        elif due['budget_due']:
            reason = 'run_budget_expired'
        elif due['lease_due']:
            reason = 'lease_expired'
        else:
            credential = token_digest(worker_token, 's') if worker_token is not None else None
            worker = self.conn.execute('''SELECT s.id FROM rt_services s JOIN rt_credentials c
                ON (s.id,s.epoch)=(c.service,c.epoch) WHERE s.id=%s AND s.epoch=%s AND s.enabled
                AND s.kind='worker' AND s.projects ? %s AND (%s::text IS NULL OR c.digest=%s)
                AND c.expires>clock_timestamp()''',
                (run['worker'], run['worker_epoch'], run['project'], credential, credential)).fetchone()
            if worker is None:
                reason = 'worker_authority_lost'
            else:
                try:
                    self.store.delegation(run, [])
                except (Denied, Error):
                    reason = 'delegation_authority_lost'
                else:
                    reason = None
        return reason, {'at': due['observed'].isoformat(), 'leaseAt': run['lease_expires'].isoformat(),
                        'runBudgetAt': run['run_deadline'].isoformat()}

    def fence(self, resource, original, worker_token):
        with self.store.unit(write=True):
            b = resource.binding
            run, _, witness, owned = self._bound(resource, b['fence'])
            require(run['state'] in ('collecting', 'stopping') and run['incident']
                    and owned['phase'] in ('armed', 'barrier', 'qa_released')
                    and owned['journalPin'] == resource.pin, 'E_STALE')
            reason, clocks = self._authority_loss(run, worker_token=worker_token)
            if reason is None:
                if original is None:
                    from .profile_unit import PinnedOriginal
                    original = PinnedOriginal(resource)
                elif getattr(original, 'process', None) is not None:
                    require(original.process.poll() is not None, 'E_AUTHORITY')
                original.absence()
                reason = 'original_supervisor_exited'
            recovery = Recovery(resource, b['fence'] + 1, run['version'] + 1)
            recovery_fields = {'fence': recovery.current_fence, 'runVersion': recovery.run_version, 'epoch': recovery.epoch}
            self.conn.execute('''UPDATE rt_runs SET state='unresolved',fence=%s,version=%s,lease_hash=NULL,
                lease_expires=NULL,incident=true,effect_witness=%s WHERE project=%s AND id=%s''',
                (recovery.current_fence, recovery.run_version, Jsonb(dict(witness,
                 interruption=dict(owned, recovery=recovery_fields, lossReason=reason, clocks=clocks))),
                 run['project'], run['id']))
            self.store.event(run, 'run_state', {'state': 'unresolved', 'reason': reason})
        return recovery, {'reason': reason, **clocks}

    def rebuild(self, project, run_id):
        """Rebuild a private operator handle from current DB authority and its held anchors."""
        with self.store.unit():
            run = self.store.run(project, run_id)
            _, witness, intent = self._intent(run)
            owned = witness['interruption']
            resource = Resource(owned['binding'], owned['anchor'], owned['journalPin'],
                                owned['resource'], owned.get('window'))
            b, anchor = resource.binding, resource.anchor
            require(run['incident'] and owned['phase'] in ('armed', 'barrier', 'qa_released', 'recovering')
                    and owned['admissionJobId'] == intent['jobId'] and digest(anchor['context']) == anchor['contextPin']
                    and (b['project'], b['run_id']) == (project, run_id), 'E_STALE')
            recovered = owned.get('recovery')
            if recovered is None:
                self._bound(resource, b['fence'])
                return resource, None
            recovery = Recovery(resource, recovered['fence'], recovered['runVersion'], recovered['epoch'])
            self._recovery(recovery)
            return resource, recovery

    def _recovery(self, recovery):
        run, snapshot, witness, owned = self._bound(recovery.resource, recovery.current_fence)
        expected = {'fence': recovery.current_fence, 'runVersion': recovery.run_version, 'epoch': recovery.epoch}
        require(run['state'] == 'unresolved' and run['version'] == recovery.run_version and run['incident']
                and owned['journalPin'] == recovery.resource.pin and owned['recovery'] == expected
                and 'observation' not in witness, 'E_STALE')
        return run, snapshot, witness, owned

    @staticmethod
    def _replacement(resource, replacement):
        ctx = resource.anchor['context']
        require(unit_anchor(replacement) == resource.anchor and replacement.name != ctx['unit']
                and replacement.ready['unit'] == replacement.name and replacement.ready['process'] != ctx['supervisor']
                and replacement.process.poll() is None, 'E_REPLACEMENT')

    def attach(self, recovery, replacement):
        with self.store.unit(write=True):
            run, _, witness, owned = self._recovery(recovery)
            resource = recovery.resource
            self._replacement(resource, replacement)
            require(owned['phase'] in ('armed', 'barrier', 'qa_released'), 'E_ONE_USE')
            reply = replacement.request('fence', binding=resource.binding, journalPin=resource.pin, epoch=recovery.epoch)
            pin = journal_pin(resource.binding, resource.anchor['contextPin'], epoch=recovery.epoch,
                              phase='identified' if resource.observed else 'consumed', resource=resource.observed)
            require(reply == {'journalPin': pin}, 'E_JOURNAL')
            local = replace(recovery, resource=replace(resource, pin=pin))
            self.last_recovery = local
            self._write(run, dict(witness, interruption=dict(owned, phase='recovering', journalPin=pin,
                recoveryPin=pin, replacement={'unit': replacement.name, 'process': replacement.ready['process']})))
        return local

    def cleanup(self, recovery, replacement, *, after_observation=None):
        with self.store.unit(write=True):
            run, snapshot, witness, owned = self._recovery(recovery)
            require(owned['phase'] == 'recovering' and owned['replacement'] ==
                    {'unit': replacement.name, 'process': replacement.ready['process']}, 'E_REPLACEMENT')
            result = self._perform(recovery, replacement, 'cleanup')
            self.last_cleanup = result
            raw = result['raw']
            resource = recovery.resource
            job = {'version': 'm50-original-admission-context-1.0.0', 'profile': resource.profile,
                   'kind': 'original_admission_context', 'admission': witness['intent'],
                   'coreTarget': snapshot['manifest']['coreTarget'], 'resourceBinding': resource.binding,
                   'contextPin': resource.anchor['contextPin'], 'originalJournalPin': owned.get('launchPin', owned['armPin']),
                   'recoveryPin': owned['recoveryPin'], 'recovery': owned['recovery']}
            observed = resource.observed or result['proof']['discovered'] or {}
            pair = {'execution': {'mode': 'executed_fixture', 'kind': 'cleanup_only', 'profile': resource.profile,
                                  'inputDigest': snapshot['input_digest'], 'recordSha256': sha(raw)},
                    'cleanup': {'containerRemoved': True, 'processesNotLive': True, 'cgroupEmpty': True,
                                'resourceIdentity': dict(observed, binding=resource.binding, barrier=resource.window)}}
            if after_observation is not None:
                after_observation(result, pair)
            ref = self.app.blobs.put(raw)
            job_ref = self.app.blobs.put(canonical(job))
            require(self.app.blobs.get(ref) == raw and self.app.blobs.get(job_ref) == canonical(job), 'E_INTEGRITY')
            current = {'project': run['project'], 'runId': run['id'], 'assignment': run['assignment'],
                       'effectNonce': run['effect_nonce'], 'attempt': run['attempt'], **owned['recovery']}
            observation = dict(pair, rawRef=ref, jobRef=job_ref, currentBinding=current)
            self._write(run, dict(witness, observation=observation,
                interruption=dict(owned, phase='cleanup_observed', journalPin=result['journalPin'])))
        return pair, {'rawSha256': ref['sha256'], 'jobSha256': job_ref['sha256'],
                      'finalJournalPin': result['journalPin'], 'quiescence': result['proof']['quiescence'],
                      'pauseRepairSha256': digest(result['proof']['pauseRepair']),
                      'removedContainerId': observed.get('containerId')}

    def safety_teardown(self, recovery, replacement):
        """Remove only the original locally pinned resource with zero server writes."""
        result = self._perform(recovery, replacement, 'safety_teardown')
        self.last_cleanup = result
        return {'kind': 'safety_teardown_only', 'proofSha256': sha(result['raw']),
                'journalPin': result['journalPin'], 'containerId': (result['proof']['discovered'] or {}).get('containerId')}

    def _perform(self, recovery, replacement, operation):
        resource = recovery.resource
        self._replacement(resource, replacement)
        # Frozen Unit flushes the exact response line to this private log before relaying it.
        with open(replacement.output_log.name, 'rb') as output:
            output.seek(0, 2)
            result = replacement.request(operation, binding=resource.binding, journalPin=resource.pin,
                                         expectedResource=resource.observed, epoch=recovery.epoch)
            raw = output.readline(128 * 1024 + 1)
        require(raw.endswith(b'\n') and strict_json(raw, 128 * 1024) == {'ok': True, 'result': result}, 'E_OBSERVATION')
        proof = result['proof']
        ctx = resource.anchor['context']
        quiet = {'unit': ctx['unit'], 'loadState': 'not-found', 'activeState': 'inactive',
                 'originalCgroupAbsent': True, 'originalProcessNotLive': True}
        stopped = proof['discovered']
        require(proof['binding'] == resource.binding and proof['operation'] == operation
                and proof['epoch'] == recovery.epoch and proof['contextPin'] == resource.anchor['contextPin']
                and proof['durableOriginal'] == resource.observed and proof['quiescence'] == quiet
                and proof['remainingContainerIds'] == [] and proof['cgroupAbsent'] is True, 'E_CLEANUP')
        if resource.window == 'before_create':
            require(stopped is None, 'E_CLEANUP')
        elif resource.window is not None or stopped is not None:
            require(stopped is not None and re.fullmatch('[a-f0-9]{64}', stopped['containerId'])
                    and (resource.observed is None or stopped['containerId'] == resource.observed['containerId'])
                    and stopped['boot'] == ctx['boot'] and stopped['initPid'] == 0 and stopped['running'] is False
                    and stopped['processes'] == {} and stopped['cgroup'] is None, 'E_CLEANUP')
        phase = 'cleaned' if operation == 'cleanup' else 'safety_only'
        require(result['journalPin'] == journal_pin(resource.binding, resource.anchor['contextPin'], epoch=recovery.epoch,
                phase=phase, resource=resource.observed, proof=proof), 'E_JOURNAL')
        return dict(result, raw=raw)

    def _accepted_cleanup(self, run, snapshot, observation, intent):
        require(observation is not None, 'E_UNRESOLVED')
        execution, cleanup = observation['execution'], observation['cleanup']
        collected = self.conn.execute('''SELECT * FROM rt_executions WHERE project=%s AND run_id=%s
            AND assignment=%s''', (run['project'], run['id'], run['assignment'])).fetchone()
        require(collected is not None and collected['work_accepted']
                and (collected['fence'], collected['effect_nonce'], collected['record_digest'], collected['cleanup']) ==
                (run['fence'], run['effect_nonce'], digest(execution), cleanup)
                and self.app.blobs.get(collected['record_ref']) == canonical(execution), 'E_UNRESOLVED')
        raw = self.app.blobs.get(observation['rawRef'])
        record = strict_json(raw)
        job, supervisor = execution['job'], observation['supervisor']
        resource = {key: record['execution'][key] for key in
                    ('containerId', 'containerName', 'containerCgroup', 'processesBefore', 'labels')}
        require(execution['mode'] == 'executed_fixture' and execution['inputDigest'] == snapshot['input_digest']
                and execution['recordSha256'] == sha(raw) and self.app.blobs.get(observation['jobRef']) == canonical(job)
                and (record['jobId'], record['runId'], record['inputHashes']) ==
                (intent['jobId'], run['id'], intent['inputHashes']) and job['executionSha256'] == sha(raw)
                and record['cleanup'] == {'containerRemoved': True, 'processesNotLive': True, 'cgroupEmpty': True}
                and cleanup == dict(record['cleanup'], resourceIdentity=resource)
                and record['execution']['containerStoppedPidZero'] is True
                and supervisor['loadState'] == 'not-found' and supervisor['cgroupAbsent'] is True
                and supervisor['workerExitCode'] == 0, 'E_UNRESOLVED')
        return {'cleanupSha256': digest(cleanup), 'rawSha256': sha(raw), 'recordDigest': collected['record_digest']}

    def fail_after_collection_expiry(self, body, worker_token):
        """Expire collected VF1 work using the independently held exact cleanup."""
        with self.store.unit(write=True):
            run = self.store.run(body['project'], body['run_id'])
            require((run['assignment'], run['fence'], run['lease_hash']) ==
                    (body['assignment'], body['fence'], token_digest(body['lease_token'], 'l'))
                    and run['state'] in ('awaiting_assessment', 'analyzing'), 'E_STALE')
            snapshot, witness, intent = self._intent(run, profile=QA_PROFILE)
            require((intent['assignment'], intent['fence']) == (run['assignment'], run['fence']), 'E_BINDING')
            reason, clocks = self._authority_loss(run, worker_token=worker_token)
            require(reason in ('lease_expired', 'run_budget_expired'), 'E_AUTHORITY')
            try:
                proof = self._accepted_cleanup(run, snapshot, witness.get('observation'), intent)
            except (Error, KeyError, TypeError, OSError):
                proof = None
            state = 'failed' if proof is not None else 'unresolved'
            reconciliation = {'reason': reason, 'originalFence': run['fence'], 'processingFence': run['fence'] + 1,
                              'cleanupProof': proof, 'state': state, **clocks}
            self.conn.execute('''UPDATE rt_runs SET state=%s,fence=fence+1,version=version+1,
                lease_hash=NULL,lease_expires=NULL,incident=%s,effect_state=%s,effect_witness=%s
                WHERE project=%s AND id=%s''', (state, proof is None, 'cleaned' if proof else 'consumed',
                Jsonb(dict(witness, postCollectionExpiry=reconciliation)), run['project'], run['id']))
            self.store.event(run, 'run_state', {'state': state, 'reason': reason})
        return reconciliation

    def fire(self, worker_token, body, admission, original, armed, *, window='after_identity'):
        with self.store.unit(worker_token, kind='worker', project=body['project'], write=True) as (actor, deadlines):
            run, witness, _, b, anchor = self._original(body, actor, deadlines, admission, original)
            owned = witness['interruption']
            require(owned['phase'] == 'armed' and b == armed.binding == owned['binding']
                    and anchor == armed.anchor == owned['anchor'] and owned['journalPin'] == armed.pin, 'E_ONE_USE')
            require(window in WINDOWS and (armed.profile == PROFILE or window == 'after_identity'), 'E_PROFILE')
            launched = original.request('fire', binding=b, journalPin=armed.pin, window=window)
            observed = launched.get('resource')
            require(launched['barrier'] == window, 'E_OBSERVATION')
            if window == 'after_identity':
                expected = 3 if armed.profile == PROFILE else 1
                require(observed['running'] is True and observed['boot'] == anchor['context']['boot']
                        and len(observed['processes']) == expected and re.fullmatch('[a-f0-9]{64}', observed['containerId'])
                        and observed['cgroup'].startswith('/sys/fs/cgroup/system.slice/' + original.name + '/containers/'), 'E_IDENTITY')
                if armed.profile == QA_PROFILE:
                    require(launched['releaseBarrier'] == 'before_fixed_checks', 'E_OBSERVATION')
            else:
                require(observed is None, 'E_IDENTITY')
            pin = journal_pin(b, anchor['contextPin'], phase='identified' if observed else 'consumed', resource=observed)
            require(launched['journalPin'] == pin, 'E_JOURNAL')
            resource = Resource(b, anchor, pin, observed, window)
            self.last_resource = resource
            self._write(run, dict(witness, interruption=dict(owned, journalPin=pin, launchPin=pin,
                                                            resource=observed, window=window, phase='barrier')))
        return resource

    def _qa_barrier(self, run, b, anchor, resource, phase):
        _, _, _, owned = self._bound(resource, b['fence'])
        require(run['state'] == 'collecting' and resource.profile == QA_PROFILE
                and resource.anchor == anchor and resource.binding == b
                and owned['phase'] == phase and resource.window == 'after_identity'
                and owned['journalPin'] == owned['launchPin'] == resource.pin, 'E_STALE')
        return owned

    def release_qa(self, worker_token, body, admission, original, resource):
        """Release the fixed checks only from a committed QA launch barrier."""
        with self.store.unit(worker_token, kind='worker', project=body['project'], write=True) as (actor, deadlines):
            run, witness, _, b, anchor = self._original(body, actor, deadlines, admission, original)
            owned = self._qa_barrier(run, b, anchor, resource, 'barrier')
            result = original.request('release', binding=b, journalPin=resource.pin)
            release_pin = digest({'operation': 'release_fixed_checks', 'journalPin': resource.pin,
                                  'contextPin': anchor['contextPin'], 'binding': b})
            require(result == {'releasePin': release_pin}, 'E_JOURNAL')
            self._write(run, dict(witness, interruption=dict(owned, phase='qa_released', releasePin=release_pin)))
        return release_pin

    def complete_qa(self, worker_token, body, admission, original, resource, release_pin):
        """Collect the original stopped, successfully released fixed QA container."""
        with self.store.unit(worker_token, kind='worker', project=body['project'], write=True) as (actor, deadlines):
            run, witness, intent, b, anchor = self._original(body, actor, deadlines, admission, original)
            owned = self._qa_barrier(run, b, anchor, resource, 'qa_released')
            require(owned['releasePin'] == release_pin, 'E_JOURNAL')
            result = original.request('finish', binding=b, journalPin=resource.pin, releasePin=release_pin)
            record = result['record']
            actual = record['execution']
            observed = resource.observed
            require((record['status'], record['runId'], record['jobId'], record['inputHashes']) ==
                    ('complete', run['id'], intent['jobId'], intent['inputHashes'])
                    and record['cleanup'] == {'containerRemoved': True, 'processesNotLive': True, 'cgroupEmpty': True}
                    and actual['exitCode'] == 0 and actual['containerStoppedPidZero'] is True
                    and (actual['containerId'], actual['containerCgroup'], actual['initPid']) ==
                    (observed['containerId'], observed['cgroup'], observed['initPid'])
                    and {pid: p['startTime'] for pid, p in actual['processesBefore'].items()} ==
                    {pid: p['startTime'] for pid, p in observed['processes'].items()}, 'E_INTEGRITY')
            proof = {'operation': 'qa_success_cleanup', 'rawRecordSha256': digest(record)}
            pin = journal_pin(b, anchor['contextPin'], phase='qa_completed', resource=observed, proof=proof)
            require(result['journalPin'] == pin, 'E_JOURNAL')
            self.last_cleanup = proof
            self._write(run, dict(witness, interruption=dict(owned, phase='qa_completed', journalPin=pin,
                normalCleanup=proof)))
        return record, {'contextPin': anchor['contextPin'], 'originalJournalPin': resource.pin, 'finalJournalPin': pin,
                        'releasePin': release_pin}
