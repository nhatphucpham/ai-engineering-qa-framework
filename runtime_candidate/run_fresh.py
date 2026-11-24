"""Exclusive live synthetic source/check/native-proposal/application acceptance."""
from contextlib import closing
import multiprocessing
from pathlib import Path
import secrets
import sys
import threading
import time
import uuid

from .application import Application, DEFAULT_CONFIG
from .common import VERSION, Error, canonical, digest, require, sha, strict_json
from .fresh_fixture import source_intake
from .run_integration import ROOT, call


def require_native_deadline(deadline):
    require(time.monotonic() < deadline, 'E_UNRESOLVED')


def await_native_ready(path, deadline, renew):
    while True:
        require_native_deadline(deadline)
        if path.exists():
            return
        renew(); time.sleep(.5)


def _ui_start(pipe):
    from .transport import CandidateClient
    with closing(pipe):
        port, cert, token, params = pipe.recv()
        result = call(CandidateClient('127.0.0.1', port, cert), 'run_start', token, **params)
        pipe.send(result)


def experiment(workspace, checks, forbidden, native_task):
    require(isinstance(native_task, str) and native_task.startswith('/root/'), 'E_INPUT')
    schema, project, run_id = 'id_' + uuid.uuid4().hex, 'freshProject', 'fresh-' + uuid.uuid4().hex[:16]
    state_root = workspace / schema
    with closing(Application(schema, state_root, create=True)) as app:
        password, changed = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        forbidden.extend((password.encode(), changed.encode()))
        app.identity.bootstrap('admin', password)
    from .test_transport import make_test_certificate
    from .transport import CandidateClient, serve
    cert, key = make_test_certificate(workspace)
    factory = lambda: Application(schema, state_root)
    server = serve(factory, cert, key)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    client = CandidateClient('127.0.0.1', server.server_address[1], cert)
    request = lambda op, token=None, **p: call(client, op, token, **p)
    try:
        access = request('session_login', user='admin', password=password)['access']; forbidden.append(access.encode())
        request('session_change_password', access, old=password, new=changed)
        admin = request('session_login', user='admin', password=changed)['access']; forbidden.append(admin.encode())
        request('project_create', admin, project=project, owner='admin')
        data = source_intake(project_id=project, task_id='freshTask', handoff_id='freshHandoff', run_id=run_id)
        with closing(factory()) as app:
            registered = app.register_snapshot(project, 'fresh_snapshot', 'repo_task', data['bundle'],
                                                sources=data['sources'], mode='executed_fixture', manifest=data['manifest'])
        config = dict(DEFAULT_CONFIG, sourceIds=sorted(data['sources']), leaseSeconds=30, runSeconds=180)
        request('project_configure', admin, project=project, expected_config=1, config=config)
        grant = request('grant_issue', admin, project=project, actions=['start', 'cancel', 'read', 'source', 'report', 'export', 'stream'], expected_config=2)['grant']
        forbidden.append(grant.encode())
        services = {}
        for kind in ('scheduler', 'worker', 'collector', 'assessor'):
            services[kind] = request('service_enroll', admin, service=kind, kind=kind, projects=[project])['credential']
            forbidden.append(services[kind].encode())
        intake = request('intake_snapshot', admin, project=project, key='fresh_intake', kind='repo_task', snapshot_ref='fresh_snapshot',
                         candidate_digest=registered['candidateDigest'], input_digest=registered['inputDigest'], expected_config=2)
        params = dict(project=project, key='fresh_start', run_id=run_id, intake_id=intake['intakeId'], grant=grant, expected_config=2)
        spawn = multiprocessing.get_context('spawn'); parent, child = spawn.Pipe()
        with closing(parent), closing(child):
            ui = spawn.Process(target=_ui_start, args=(child,)); ui.start(); child.close()
            try:
                parent.send((server.server_address[1], cert, admin, params))
                require(parent.poll(30), 'E_DEPENDENCY'); started = parent.recv(); ui.join(10)
                require(ui.exitcode == 0 and started['state'] == 'queued', 'E_INTEGRITY')
            finally:
                if ui.is_alive(): ui.terminate(); ui.join(10)
                require(not ui.is_alive(), 'E_UNRESOLVED'); ui.close()
        assignment = request('worker_claim', services['scheduler'], project=project, worker='worker', expected_run_version=1, run_id=run_id)
        body = dict(project=project, run_id=run_id, **{k: assignment[k] for k in ('assignment', 'fence', 'lease_token')})
        forbidden.append(body['lease_token'].encode())
        admission = request('worker_admit', services['worker'], **body)
        checks['F01'] = {'status': 'PASS', 'sourceArtifacts': len(data['sources']), 'importedObservations': 0,
                         'actualUiProcessExitedBeforeWorker': True, 'distinctRawJobAndHeldHandoff': admission['jobId'] != 'freshHandoff'}
        output = workspace / 'fresh_execution'; output.mkdir()
        from .fixed_executor import execute
        renewal_count = 0
        def renew():
            nonlocal renewal_count
            request('worker_renew', services['worker'], **body); renewal_count += 1
        from spikes.m50_worker.controller import Controller, collection_body
        from spikes.m50_worker.qa_executor import ExecutionInterrupted
        try:
            with closing(factory()) as app:
                record, supervisor = execute(output, ROOT / '.cache/s6/vf1' / workspace.name / 'fresh', run_id,
                    admission['jobId'], admission['manifest']['inputHashes'], renew,
                    controller=Controller(app), worker_token=services['worker'], body=body, admission=admission)
        except ExecutionInterrupted as exc:
            if exc.pair is not None:
                cleanup = request('collector_record', services['collector'], **collection_body(exc.recovery, exc.pair))
                require(cleanup['cleanupOnly'] and not cleanup['accepted'], 'E_INTEGRITY')
            raise
        extracted_sha = digest(record)
        emitted_sha = sha((output / 'worker.stdout.json').read_bytes())
        record['ingestionIntervention'] = {'withheldTestIds': [], 'appliedBeforeHostRequest': True}
        raw = canonical(record); (output / 'execution.json').write_bytes(raw)
        from spikes.vf1.run_vf1 import build_job, staged_payloads
        staging = ROOT / '.cache/s6/vf1' / workspace.name / 'fresh'
        job = build_job(record, sha(raw), [], staged_payloads(staging, record['inputHashes']))
        effect = dict(project=project, run_id=run_id, assignment=body['assignment'], fence=body['fence'], effect_nonce=admission['effectNonce'])
        def rejected_collection(pair):
            try:
                request('collector_record', services['collector'], **effect, **pair)
            except Error as exc:
                require(exc.code == 'E_UNRESOLVED', 'E_INTEGRITY')
            else:
                raise Error('E_INTEGRITY')
            with closing(factory()) as app, app.store.unit():
                require(app.conn.execute('SELECT count(*) AS n FROM rt_executions').fetchone()['n'] == 0
                        and app.store.run(project, run_id)['state'] == 'collecting', 'E_INTEGRITY')
        claimed = {'execution': {'mode': 'executed_fixture', 'inputDigest': registered['inputDigest'], 'job': job, 'recordSha256': sha(raw)},
                   'cleanup': dict(record['cleanup'], resourceIdentity={key: record['execution'][key] for key in
                                   ('containerId', 'containerName', 'containerCgroup', 'processesBefore', 'labels')})}
        rejected_collection(claimed)
        with closing(factory()) as app:
            observation = app.observe_executor(project, run_id, admission['effectNonce'], raw, job, supervisor)
        altered = dict(observation, cleanup=dict(observation['cleanup'], resourceIdentity=dict(observation['cleanup']['resourceIdentity'], containerId='0' * 64)))
        rejected_collection(altered)
        observed = request('collector_record', services['collector'], **effect, **observation)
        require(observed['accepted'] and not observed['cleanupOnly'], 'E_INTEGRITY')
        checks['F02'] = {'status': 'PASS', 'counts': record['execution']['counts'], 'actualRootlessExecution': True,
                         'renewalsDuringExecution': renewal_count, 'cleanupObserved': True, 'separateCollectorAccepted': True,
                         'supervisorRelayTranscriptSha256': emitted_sha, 'transcriptFormat': 'original emitted JSONL',
                         'extractedWorkerRecordSha256': extracted_sha, 'enrichedRecordSha256': sha(raw),
                         'enrichment': 'only explicit ingestionIntervention, no withheld observations',
                         'jobDigest': digest(job), 'inputHashes': record['inputHashes'], 'heldInputPinsMatchedBeforeLaunch': True,
                         'validCollectorBeforeWitnessDenied': True, 'changedResourceProofDenied': True, 'noExecutionRowOnDenial': True}
        from spikes.hc1.orchestrator import response_contract
        contract = response_contract(job)
        contract['version'] = 'm50-native-response-contract-1.0.0'
        relation = ('Evidence-review reference rule: the bridge includes only observations referenced by bindings in its handoff. '
                    'Therefore evidenceReviews must contain each bound evidenceId exactly once and no unbound observation IDs. '
                    'You may inspect any offered observation while reasoning, but omit its evidenceReview unless a binding uses it. '
                    'Do not invent a binding merely to retain an unused review. This is a reference-integrity rule, not a requested QA conclusion.')
        contract['instructions'] += '\n\n' + relation
        contract['schema']['properties']['evidenceReviews']['description'] = relation
        offer = {'request': job, 'responseContract': contract, 'dispatch': {'jobDigest': digest(job)}}
        offer_path = workspace / 'native-offer.json'; offer_path.write_bytes(canonical(offer))
        dispatch = {'version': 'm50-native-dispatch-1.0.0', 'nativeTask': native_task,
                    'jobDigest': digest(job), 'offerSha256': sha(offer_path.read_bytes()),
                    'maxSubmissions': 3, 'correctionWindowSeconds': 120,
                    'attestationScope': 'issuer session observes native task; task metadata is not model authentication'}
        (workspace / 'native-dispatch.json').write_bytes(canonical(dispatch))
        print('FRESH_NATIVE_OFFER_READY ' + str(offer_path), flush=True)
        deadline = time.monotonic() + 120
        from .execution_projection import project as project_inputs
        from .publication import prepare
        target = {'projectId': project, 'taskRef': 'freshTask', 'handoffId': 'freshHandoff', 'runId': run_id,
                  'projectConfigVersion': 2, 'dataPolicyVersion': 2, 'candidateRevision': 'mock-06-head-v1', 'requirementVersion': 'mock-req-06-v1'}
        from spikes.vf1.core_bridge import BridgeError
        from qa_core.rules import AssessmentError, evaluate
        for submission in range(1, dispatch['maxSubmissions'] + 1):
            ready_path = workspace / ('native-ready-' + str(submission) + '.json')
            await_native_ready(ready_path, deadline, renew)
            require_native_deadline(deadline)
            ready = strict_json(ready_path.read_bytes())
            proposal_path = workspace / ('native-response-' + str(submission) + '.json')
            proposal_raw = proposal_path.read_bytes()
            require(ready == {'nativeTask': native_task, 'jobDigest': digest(job), 'offerSha256': dispatch['offerSha256'],
                              'responseSha256': sha(proposal_raw), 'observedNativeCompletion': True}, 'E_INTEGRITY')
            try:
                proposal = strict_json(proposal_raw)
                inputs = project_inputs(job, proposal, target)
                evaluate(inputs['bundle'], inputs['assessment'])
                prepare(inputs['bundle'], inputs['assessment'], expected_bundle_digest=digest(inputs['bundle']),
                        expected_assessment_digest=digest(inputs['assessment']), run_id=run_id, report_id='report_' + run_id)
                require_native_deadline(deadline)
            except (Error, BridgeError, AssessmentError) as exc:
                rejection = {'submission': submission, 'nativeTask': native_task, 'responseSha256': sha(proposal_raw),
                             'jobDigest': digest(job), 'accepted': False, 'code': getattr(exc, 'code', 'E_INTEGRITY')}
                if isinstance(exc, AssessmentError):
                    rejection['diagnostics'] = exc.errors
                    if exc.errors and isinstance(exc.errors[0].get('code'), str):
                        rejection['code'] = exc.errors[0]['code']
                (workspace / ('native-rejection-' + str(submission) + '.json')).write_bytes(canonical(rejection))
                print('FRESH_NATIVE_PROPOSAL_REJECTED ' + str(submission) + ' ' + rejection['code'], flush=True)
                continue
            break
        else:
            raise Error('E_BUDGET')
        require_native_deadline(deadline)
        accepted = request('assessment_accept', services['assessor'], **effect, bundle=inputs['bundle'], assessment=inputs['assessment'],
                           bundle_digest=digest(inputs['bundle']), assessment_digest=digest(inputs['assessment']), execution_digest=observed['executionDigest'])
        result = request('worker_submit', services['worker'], **body, assessment_digest=accepted['assessmentDigest'])
        require(result['state'] == 'completed', 'E_INTEGRITY')
        report = request('report_read', admin, project=project, run_id=run_id)
        require(report['view']['humanDecision'] == 'pending' and report['view']['verification'] == 'failed', 'E_INTEGRITY')
        require(request('report_export', admin, project=project, run_id=run_id)['view'] == report['view'], 'E_INTEGRITY')
        sources = {link['artifactId'] for group in report['sourceLinks'] for link in group['links'] if 'artifactId' in link}
        for aid in sources:
            item = request('source_read', admin, project=project, run_id=run_id, artifact_id=aid)
            require(item['text'].encode() == data['sources'][aid][0], 'E_INTEGRITY')
        events = client.events(project, run_id, admin)
        require(len([r for r in events if r['event'] == 'report_ready']) == 1, 'E_INTEGRITY')
        checks['F03'] = {'status': 'PASS', 'nativeTask': native_task, 'nativeSubmission': submission,
                         'nativeAttestation': 'issuer-recorded session task completion and exact offer/response hashes',
                         'freshNativeProposalSha256': sha(proposal_raw), 'offerSha256': dispatch['offerSha256'], 'heldContext': target,
                         'statuses': [c['status'] for c in report['view']['criteria']], 'safeSourceLinksResolved': len(sources),
                         'humanDecision': 'pending', 'oneReportReady': True, 'viewSha256': report['viewSha256']}
        # Actual restore includes populated rawRef and jobRef and rechecks both bytes.
        from .checkpoint import backup, restore
        with closing(factory()) as app:
            receipt = backup(app.store, workspace / 'fresh_backup')
            new_schema, new_root = 'id_' + uuid.uuid4().hex, workspace / 'fresh_restore'
            restored = restore(app.store, workspace / 'fresh_backup', checkpoint=receipt, target_schema=new_schema, target_root=new_root, activate=True)
        require(restored['state'] == 'active_restore', 'E_INTEGRITY')
        with closing(Application(new_schema, new_root)) as app:
            obs = app.store.run(project, run_id)['effect_witness']['observation']
            require(app.blobs.get(obs['rawRef']) == raw and app.blobs.get(obs['jobRef']) == canonical(job), 'E_INTEGRITY')
        from .checkpoint_cases import listener
        with listener({'certificate': cert, 'private_key': key}, new_schema, new_root) as restored_client:
            require(call(restored_client, 'report_read', admin, project=project, run_id=run_id) == report, 'E_INTEGRITY')
        checks['F04'] = {'status': 'PASS', 'actualPopulatedWitnessBackupRestore': True, 'rawAndOfferedJobBytesExact': True,
                         'ordinaryReportExactAfterCutover': True, 'blobCount': receipt['blobCount']}
        return {'schema': schema, 'stateRoot': str(state_root.relative_to(ROOT)), 'project': project, 'runId': run_id}
    except Exception:
        # A missing/rejected native proposal is a processing failure. Reuse only
        # already independently accepted cleanup; never invent an execution result.
        if 'body' in locals() and 'services' in locals():
            failure = {'status': 'OBSERVED', 'scope': 'processing failure, not criterion verification'}
            try:
                state = request('run_read', admin, project=project, run_id=run_id)
                if state['state'] in ('collecting', 'awaiting_assessment', 'analyzing'):
                    request('worker_fail', services['worker'], **body,
                            code='assessment_missing' if 'F02' in checks else 'check_error')
                    try:
                        request('worker_observe_cleanup', services['worker'], **body)
                    except Error as exc:
                        failure['cleanupAckDenied'] = exc.code
                state = request('run_read', admin, project=project, run_id=run_id)
                failure.update(processingState=state['state'], incidentOpen=state['incidentOpen'])
            except Error as exc:
                failure['authorityError'] = exc.code
            checks['F99'] = failure
        raise
    finally:
        server.shutdown(); server.server_close(); thread.join(5)
        require(not thread.is_alive(), 'E_UNRESOLVED')


if __name__ == '__main__':
    from .run_integration import main
    require(len(sys.argv) == 3, 'E_INPUT')
    native_task = sys.argv.pop()
    raise SystemExit(main(experiment_fn=lambda workspace, checks, forbidden: experiment(workspace, checks, forbidden, native_task)))
