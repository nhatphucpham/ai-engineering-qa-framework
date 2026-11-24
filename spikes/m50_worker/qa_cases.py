"""Actual normal-profile cancellation and collected-work expiry acceptance."""
from contextlib import closing
import os
import time

from runtime_candidate.common import Error, canonical, digest, require, sha
from runtime_candidate.storage import Jsonb
from spikes.s4f.unit import ROOT
from spikes.vf1.run_vf1 import build_job, staged_payloads

from .actors import actor, collector_process, driver_process, ui_process
from .controller import Controller, QA_PROFILE, collection_body
from .fixture import deny, fixture, graph
from .profile_unit import ProfileUnit
from .qa_executor import ExecutionInterrupted, execute_qa


def _collect(collector, payload):
    collector.send('collect', payload)
    result = collector.receive('collector_response')
    require('result' in result, 'E_COLLECTOR')
    return result['result']


def _renew(driver):
    driver.send('renew')
    response = driver.receive('worker_response')
    if 'denied' in response:
        raise Error(response['denied'])
    return response['result']


def _no_publication(view):
    require((view['assessments'], view['reports'], view['ready']) == (0, 0, 0)
            and all(event['event'] != 'report_ready' for event in view['events']), 'E_PUBLICATION')


def _normal_cancel(f, controller, driver, collector, launch):
    seen = {}
    app = controller.app

    def cancel(original, resource):
        with closing(ProfileUnit('observer', launch['output'], resource.anchor)) as observer:
            live = observer.request('observe', binding=resource.binding, journalPin=resource.pin)
            require(live['resource'] == resource.observed and live['resource']['running'] is True
                    and len(live['resource']['processes']) == 1 and live['releaseBarrierClosed'] is True
                    and live['observer'] != original.ready['process'], 'E_OBSERVATION')
        before = graph(app, f.scope)
        require(before['state'] == 'collecting' and before['incident'] and before['executions'] == [], 'E_STALE')
        stopping = f.request('run_cancel', f.admin, **f.scope, key='cancel_normal',
                             grant=f.start['grant'], expected_version=before['version'])
        require(stopping['state'] == 'stopping' and stopping['incidentOpen'], 'E_CANCEL')
        stopped = graph(app, f.scope)
        require(stopped['state'] == 'stopping' and stopped['executions'] == [] and not stopped['hasObservation'], 'E_CANCEL')
        _no_publication(stopped)
        seen.update(resource=live['resource'], independentObserver=live['observer'], observerAbsence=observer.absence(),
                    before=before, stopping=stopped, preCheckReleaseBarrier=live['releaseBarrierClosed'])

    try:
        execute_qa(**launch, after_live=cancel)
    except ExecutionInterrupted as interrupted:
        require(interrupted.code == 'E_STALE' and interrupted.reconciliation_error is None
                and interrupted.recovery is not None and interrupted.pair is not None and seen, 'E_NORMAL_RECOVERY')
        unresolved = graph(app, f.scope)
        payload = collection_body(interrupted.recovery, interrupted.pair)
        require(unresolved['state'] == 'unresolved' and unresolved['incident'] and unresolved['hasObservation']
                and unresolved['executions'] == [] and payload['execution']['profile'] == QA_PROFILE
                and payload['execution']['kind'] == 'cleanup_only'
                and interrupted.proof['loss']['reason'] == 'cancelled_by_user', 'E_NORMAL_RECOVERY')
        _no_publication(unresolved)
        accepted = _collect(collector, payload)
        final = graph(app, f.scope)
        require(accepted == {'accepted': False, 'cleanupOnly': True, 'executionDigest': digest(payload['execution'])}
                and final['state'] == 'cancelled' and not final['incident'] and len(final['executions']) == 1
                and final['executions'][0]['work_accepted'] is False
                and final['executions'][0]['fence'] == unresolved['fence'] == seen['before']['fence'] + 1
                and final['executions'][0]['collector'] == 'collector', 'E_NORMAL_RECOVERY')
        _no_publication(final)
        seen.update(unresolved=unresolved, final=final, cleanup=interrupted.proof,
                    cleanupExecutionSha256=accepted['executionDigest'],
                    monitor=driver.receive('authority_loss'))
        return seen
    raise Error('E_NORMAL_RECOVERY')


def _break_raw_reference(app, body, raw, output):
    """Apply one explicit database fault to this disposable fixture."""
    with app.store.unit(write=True) as (_, deadlines):
        run = app.store.run(body['project'], body['run_id'])
        require(run['state'] == 'awaiting_assessment' and (run['assignment'], run['fence']) ==
                (body['assignment'], body['fence']), 'E_STALE')
        app.store.current_work(run, deadlines)
        witness = run['effect_witness']
        observation = witness['observation']
        original = observation['rawRef']
        missing = dict(original, sha256='0' * 64)
        require(original != missing and app.blobs.get(original) == raw, 'E_INTEGRITY')
        denied = deny(lambda: app.blobs.get(missing), 'E_INTEGRITY')
        audit = {'kind': 'operator_fixture_missing_cleanup_reference',
                 'project': run['project'], 'runId': run['id'], 'assignment': run['assignment'], 'fence': run['fence'],
                 'originalObservationSha256': digest(observation), 'originalRawRef': original, 'substitutedRawRef': missing}
        archived = canonical(audit)
        with (output / 'operator-missing-cleanup-reference.json').open('xb') as stream:
            stream.write(archived)
            stream.flush()
            os.fsync(stream.fileno())
        altered = dict(witness, observation=dict(observation, rawRef=missing))
        row = app.conn.execute('''UPDATE rt_runs SET effect_witness=%s WHERE project=%s AND id=%s
            AND assignment=%s AND fence=%s AND effect_witness=%s RETURNING id''',
            (Jsonb(altered), run['project'], run['id'], run['assignment'], run['fence'], Jsonb(witness))).fetchone()
        require(row is not None, 'E_STALE')
    return dict(audit, privateArchiveSha256=sha(archived), nonexistentBlobDenied=denied)


def _post_collection_expiry(f, controller, driver, collector, launch, *, missing_proof):
    app = controller.app
    record, supervisor = execute_qa(**launch)
    require(record['status'] == 'complete' and record['execution']['observations'], 'E_OBSERVATION')
    raw = canonical(dict(record, ingestionIntervention={'withheldTestIds': [], 'appliedBeforeHostRequest': True}))
    job = build_job(record, sha(raw), [], staged_payloads(launch['staging'], record['inputHashes']))
    body, admission = launch['body'], launch['admission']
    pair = app.observe_executor(f.scope['project'], f.scope['run_id'], admission['effectNonce'], raw, job, supervisor)
    bound = dict(f.scope, assignment=body['assignment'], fence=body['fence'], effect_nonce=admission['effectNonce'])
    collected = _collect(collector, dict(bound, **pair))
    require(collected['accepted'] and not collected['cleanupOnly'], 'E_OBSERVATION')
    before = graph(app, f.scope)
    require(before['state'] == 'awaiting_assessment' and before['hasObservation']
            and len(before['executions']) == 1 and before['executions'][0]['work_accepted'], 'E_OBSERVATION')
    _no_publication(before)
    premature = deny(lambda: controller.fail_after_collection_expiry(body, f.services['worker']), 'E_AUTHORITY')
    require(graph(app, f.scope) == before, 'E_INTEGRITY')
    fault = None
    before_expiry = before
    if missing_proof:
        fault = _break_raw_reference(app, body, raw, launch['output'])
        before_expiry = graph(app, f.scope)
        require(before_expiry['witnessSha256'] != before['witnessSha256']
                and dict(before_expiry, witnessSha256=before['witnessSha256']) == before, 'E_INTEGRITY')
    monitor = driver.receive('authority_loss', timeout=30)
    require(monitor['code'] == 'E_STALE' and monitor['positivePolls'] > 0, 'E_STALE')
    # This deliberately invalid offer verifies that expiry fences the assessor before
    # input acceptance. It supplies no observations, assessment, or model outcome.
    invalid_offer = dict(bound, bundle={}, assessment={}, bundle_digest=digest({}),
                         assessment_digest=digest({}), execution_digest=collected['executionDigest'])
    expired_assessor = deny(lambda: f.request('assessment_accept', f.services['assessor'], **invalid_offer), 'E_STALE')
    require(graph(app, f.scope) == before_expiry, 'E_INTEGRITY')
    reconciliation = controller.fail_after_collection_expiry(body, f.services['worker'])
    state = 'unresolved' if missing_proof else 'failed'
    proof = None if missing_proof else {'cleanupSha256': digest(pair['cleanup']), 'rawSha256': sha(raw),
                                       'recordDigest': collected['executionDigest']}
    require(reconciliation['state'] == state and reconciliation['reason'] == 'lease_expired'
            and reconciliation['cleanupProof'] == proof, 'E_RECONCILIATION')
    after = graph(app, f.scope)
    require(after['state'] == state and after['incident'] is missing_proof and after['fence'] == before['fence'] + 1
            and after['executions'] == before['executions'] and after['hasObservation'], 'E_RECONCILIATION')
    _no_publication(after)
    replay = deny(lambda: f.request('assessment_accept', f.services['assessor'], **invalid_offer), 'E_STALE')
    report = deny(lambda: f.request('report_read', f.admin, **f.scope), 'E_DENIED')
    driver.send('publish', digest({}))
    publication = driver.receive('worker_response')
    require(publication == {'denied': 'E_STALE'} and graph(app, f.scope) == after, 'E_PUBLICATION')
    with app.store.unit():
        observation = app.store.run(f.scope['project'], f.scope['run_id'])['effect_witness']['observation']
        original = observation['rawRef']
        if fault is not None:
            require(original == fault['substitutedRawRef'], 'E_INTEGRITY')
            deny(lambda: app.blobs.get(original), 'E_INTEGRITY')
            original = fault['originalRawRef']
            require(digest(dict(observation, rawRef=original)) == fault['originalObservationSha256'], 'E_INTEGRITY')
        require(app.blobs.get(original) == raw and app.blobs.get(observation['jobRef']) == canonical(job), 'E_INTEGRITY')
    result = {'before': before, 'final': after, 'monitor': monitor, 'reconciliation': reconciliation,
            'beforeExpiryDenied': premature, 'afterExpiryAssessmentDenied': expired_assessor,
            'staleFenceAssessmentDenied': replay, 'staleWorkerPublishDenied': publication['denied'],
            'reportDenied': report, 'supervisor': supervisor,
            'rawRefSha256': sha(raw), 'jobRefSha256': digest(job), 'actualCounts': record['execution']['counts']}
    if fault is not None:
        result.update(operatorFault=fault, beforeExpiry=before_expiry, originalProofBlobRetained=True)
    return result


def run_case(work, certificate, private_key, forbidden, *, case):
    require(case in ('normal_cancel', 'post_collection_expiry', 'post_collection_missing_proof'), 'E_INPUT')
    lease = 45 if case == 'normal_cancel' else 15
    with fixture(work, certificate, private_key, forbidden, profile=QA_PROFILE, lease=lease, budget=150) as f:
        output = work / 'profile_output'
        output.mkdir()
        staging = ROOT / '.cache/s6/vf1' / ('m50_worker_' + work.parent.name) / work.name
        with actor(ui_process, (f.endpoint, f.admin, f.start)) as ui:
            started = ui.receive('started')
            require(started['result']['state'] == 'queued', 'E_INPUT')
            ui.send('exit')
            ui_exit = ui.join()
        with (actor(driver_process, (f.endpoint, f.scope, f.services['scheduler'], f.services['worker'])) as driver,
              actor(collector_process, (f.endpoint, f.services['collector'])) as collector,
              closing(f.factory()) as app):
            assigned = driver.receive('admitted')
            admissions = assigned['admission']
            forbidden.append(assigned['body']['lease_token'].encode())
            require(admissions['manifest']['checkRegistry'] == QA_PROFILE and admissions['manifest']['inputHashes'],
                    'E_PROFILE')
            positive = driver.receive('monitoring')
            collector_pid = collector.receive('ready')['pid']
            controller = Controller(app)
            launch = dict(output=output, staging=staging, run_id=f.scope['run_id'], job_id=admissions['jobId'],
                          held_input_hashes=admissions['manifest']['inputHashes'], check_authority=lambda: _renew(driver),
                          controller=controller, worker_token=f.services['worker'], body=assigned['body'], admission=admissions)
            if case == 'normal_cancel':
                checks = _normal_cancel(f, controller, driver, collector, launch)
            else:
                checks = _post_collection_expiry(f, controller, driver, collector, launch,
                                                 missing_proof=case == 'post_collection_missing_proof')
            require(len({ui_exit['pid'], assigned['pid'], collector_pid}) == 3, 'E_ACTOR_EXIT')
            driver.send('exit')
            collector.send('exit')
            return {'status': 'PASS', 'profile': QA_PROFILE, 'schema': f.schema, 'scope': f.scope,
                    'coreTarget': f.core_target, 'inputPinsSha256': digest(admissions['manifest']['inputHashes']),
                    'ui': ui_exit, 'driver': driver.join(), 'collector': collector.join(),
                    'oneUseAdmission': positive['duplicateAdmission'], **checks}
