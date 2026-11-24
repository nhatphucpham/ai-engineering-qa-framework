"""Serialized M50 application worker acceptance against synthetic loopback fixtures."""
import base64
from contextlib import closing, contextmanager
import ctypes
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import traceback
import uuid

from runtime_candidate.common import Error, VERSION, canonical, digest, require, sha


ROOT = Path(__file__).resolve().parents[2]
CASES = (
    ('ui-exit-user-cancel', 'cancel', 'after_identity', 60, 110),
    ('worker-revocation', 'revoke', 'after_identity', 60, 110),
    ('real-lease-expiry', 'lease', 'after_identity', 40, 100),
    ('real-run-budget-expiry', 'budget', 'after_identity', 80, 40),
    ('whole-supervisor-loss', 'unit', 'after_identity', 60, 110),
    ('before-create', 'cancel', 'before_create', 60, 110),
    ('after-start-before-identity', 'cancel', 'after_start', 60, 110),
    ('newer-server-head', 'newer_head', 'after_identity', 60, 110),
    ('unknown-external-head', 'unknown_head', 'after_identity', 60, 110),
    ('lost-cleanup-ack', 'lost_ack', 'after_identity', 60, 110),
    ('durable-coordinator-restart', 'restart', 'after_identity', 60, 110),
)
QA_CASES = ('normal_cancel', 'post_collection_expiry', 'post_collection_missing_proof')


def source_pins():
    folders = ('runtime_candidate', 'qa_core', 'schemas', 'spikes/m50_worker', 'spikes/s4f',
               'spikes/s4', 'spikes/s4b', 'spikes/vf1', 'spikes/s2', 'spikes/s6b',
               'examples/mock/06-filter-pagination')
    extensions = {'.py', '.sql', '.json', '.md', '.lock', '.diff', '.txt'}
    paths = {path for folder in folders for path in (ROOT / folder).rglob('*')
             if path.suffix in extensions and path.is_file() and '__pycache__' not in path.parts}
    paths.update(ROOT / name for name in ('docs/M50-WORKER-CONTROLLER-PROTOCOL.md', 'docs/S4-F-PROTOCOL.md'))
    return {path.relative_to(ROOT).as_posix(): sha(path.read_bytes()) for path in sorted(paths)}


def _safe_error(exc):
    code = getattr(exc, 'code', str(exc))
    return {'type': type(exc).__name__, 'code': code if isinstance(code, str)
            and re.fullmatch(r'E_[A-Z_]{1,45}', code) else 'E_CAMPAIGN',
            'frames': [{'file': Path(frame.filename).name, 'line': frame.lineno, 'function': frame.name}
                       for frame in traceback.extract_tb(exc.__traceback__)]}


def _db_state(app, scope, *, authority_fault=False):
    from .fixture import graph
    return graph(app, scope, inspect_fault=authority_fault)


def _empty_progress(graph):
    require(graph['assessments'] == graph['reports'] == graph['ready'] == 0
            and all(row['event'] not in ('check_completed', 'report_ready') for row in graph['events']), 'E_PROGRESS')


def _no_acceptance(graph, state, *, observation=False):
    _empty_progress(graph)
    require(graph['state'] == state and graph['incident'] is True and not graph['executions']
            and graph['hasObservation'] is observation, 'E_GRAPH')


def _resource_record(resource):
    context = resource.anchor['context']
    return {'profile': resource.profile, 'contextPin': resource.anchor['contextPin'],
            'contextAnchorSha256': digest(resource.anchor), 'originalUnit': context['unit'],
            'invocation': context['invocation'], 'originalProcess': context['supervisor'], 'boot': context['boot'],
            'image': context['image'], 'journalPin': resource.pin, 'binding': resource.binding,
            'window': resource.window, 'durableResource': resource.observed}


def _closed_unit(unit):
    result = unit.close()
    require(unit.process.poll() is not None and unit.closed and not unit.thread.is_alive(), 'E_UNIT_REMAINS')
    return {**result, 'relayPid': unit.process.pid, 'relayExitCode': unit.process.returncode}


def _observe(resource, workspace):
    from spikes.s4f.unit import Unit
    with closing(Unit('observer', workspace, resource.anchor)) as observer:
        observation = observer.request('observe', binding=resource.binding, journalPin=resource.pin)
        closed = _closed_unit(observer)
    return dict(observation, unitAbsence=closed)


def _denial_request(client, op, token, body, *codes):
    from .actors import request
    from .fixture import deny
    return deny(lambda: request(client, op, token, **body), *codes)


def _monitor(pipe, client, worker, body, original, resource, workspace):
    from .actors import request
    from .fixture import deny
    polls = 1  # The coordinator proved one live, consumed admission before publishing the barrier.
    end = time.monotonic() + 135
    while time.monotonic() < end:
        if pipe.poll(.25):
            action, value = pipe.recv()
            require(value is None, 'E_CHANNEL')
            if action == 'inspect':
                require(original.process.poll() is None, 'E_UNIT_REMAINS')
                observed = _observe(resource, workspace)
                require(original.process.poll() is None, 'E_UNIT_REMAINS')
                pipe.send(('inspected', dict(observed, coordinatorPid=os.getpid())))
            elif action == 'kill_original':
                return {'signal': 'original_unit_exit', 'positivePolls': polls, 'kill': original.kill_original()}
            elif action == 'abort':
                raise Error('E_PARENT_ABORT')
            else:
                raise Error('E_CHANNEL')
        if original.process.poll() is not None:
            return {'signal': 'original_unit_exit', 'positivePolls': polls}
        code = deny(lambda: request(client, 'worker_admit', worker, **body), 'E_CONFLICT',
                    'E_AUTH', 'E_DENIED', 'E_STALE', 'E_UNRESOLVED')
        if code != 'E_CONFLICT':
            return {'signal': code, 'positivePolls': polls}
        polls += 1
    raise Error('E_MONITOR')


def _operator_fault(app, scope, kind):
    if kind == 'newer_head':
        with app.store.unit(write=True):
            row = app.store.run(scope['project'], scope['run_id'])
            assignment = uuid.uuid4().hex
            result = app.conn.execute('''UPDATE rt_runs SET assignment=%s,fence=fence+1,version=version+1
                WHERE project=%s AND id=%s AND fence=%s AND version=%s RETURNING assignment,fence,version''',
                (assignment, scope['project'], scope['run_id'], row['fence'], row['version'])).fetchone()
            require(result is not None, 'E_FAULT')
        return {'kind': 'operator_fixture_newer_assignment', 'priorFence': row['fence'], **result}
    require(kind == 'unknown_head', 'E_FAULT')
    with app.identity.tx():
        old = app.store._check_witness()
        injected = dict(old, nonce=uuid.uuid4().hex)
        app.store._save_witness(injected)
    return {'kind': 'operator_fixture_external_head', 'databaseHeadSha256': digest(old),
            'externalHeadSha256': digest(injected)}


def _lost_cleanup_ack(controller, recovery, replacement):
    from .fixture import deny
    observed = {}

    def abort_after_observation(result, pair):
        observed.update(pair=pair, externalProofSha256=sha(result['raw']), externalJournalPin=result['journalPin'],
                        removal=result['proof']['remainingContainerIds'] == [], quiescence=result['proof']['quiescence'])
        raise Error('E_LOST_ACK')

    first = deny(lambda: controller.cleanup(recovery, replacement, after_observation=abort_after_observation), 'E_LOST_ACK')
    require(observed['removal'] and observed['externalJournalPin'] != recovery.resource.pin, 'E_CLEANUP')
    retry = deny(lambda: controller.cleanup(recovery, replacement), 'E_JOURNAL')
    pair = observed.pop('pair')
    return pair, {'fault': first, 'retry': retry, **observed}


def _finish_recovery(controller, recovery, scope, mode, workspace, progress):
    from .fixture import deny
    from spikes.s4f.unit import Unit

    with closing(Unit('replacement', workspace, recovery.resource.anchor)) as replacement:
        attached = controller.attach(recovery, replacement)
        progress['replacement'] = {'unit': replacement.name, 'process': replacement.ready['process'],
                                   'attachedContextPin': replacement.ready['contextPin'],
                                   'recoveryPin': attached.resource.pin, 'epoch': attached.epoch}
        before = _db_state(controller.app, scope)
        _no_acceptance(before, 'unresolved')
        progress['beforeCleanup'] = before
        pair = None
        try:
            if mode in ('newer_head', 'unknown_head'):
                progress['injectedFault'] = _operator_fault(controller.app, scope, mode)
                unknown = mode == 'unknown_head'
                held = _db_state(controller.app, scope, authority_fault=unknown)
                _no_acceptance(held, 'unresolved')
                size = Path(replacement.output_log.name).stat().st_size
                rejected = deny(lambda: controller.cleanup(attached, replacement), 'E_UNRESOLVED' if unknown else 'E_STALE')
                require(Path(replacement.output_log.name).stat().st_size == size, 'E_PREMATURE_IO')
                require(_db_state(controller.app, scope, authority_fault=unknown) == held, 'E_GRAPH')
                progress['applicationCleanupDenied'] = rejected
                progress['safetyTeardown'] = controller.safety_teardown(attached, replacement)
                require(_db_state(controller.app, scope, authority_fault=unknown) == held, 'E_GRAPH')
                progress['afterCleanup'] = held
            elif mode == 'lost_ack':
                pair, progress['unacknowledgedCleanup'] = _lost_cleanup_ack(controller, attached, replacement)
                progress['afterCleanup'] = _db_state(controller.app, scope)
                require(progress['afterCleanup'] == before, 'E_GRAPH')
            else:
                pair, progress['cleanup'] = controller.cleanup(attached, replacement)
                progress['afterCleanup'] = _db_state(controller.app, scope)
                _no_acceptance(progress['afterCleanup'], 'unresolved', observation=True)
        except Exception:
            if controller.last_cleanup is None and attached.resource.observed is not None:
                try:
                    progress['exceptionSafetyTeardown'] = controller.safety_teardown(attached, replacement)
                except Exception as exc:
                    progress['exceptionCleanupUnresolved'] = _safe_error(exc)
            raise
        finally:
            progress['replacement']['absence'] = _closed_unit(replacement)
    return attached, pair


def _teardown_after_error(controller, scope, workspace, progress):
    from .profile_unit import PinnedOriginal
    from spikes.s4f.unit import Unit

    if 'replacement' in progress:
        return  # The replacement path already evaluated its exact safety option.
    try:
        resource, recovery = controller.rebuild(scope['project'], scope['run_id'])
        require(resource.observed is not None, 'E_UNRESOLVED')
        original = PinnedOriginal(resource)
        progress['errorOriginalAbsence'] = original.kill_original()
        if recovery is None:
            recovery, _ = controller.fence(resource, None, None)
        with closing(Unit('replacement', workspace, resource.anchor)) as replacement:
            try:
                recovery = controller.attach(recovery, replacement)
                progress['errorSafetyTeardown'] = controller.safety_teardown(recovery, replacement)
            finally:
                progress['errorReplacementAbsence'] = _closed_unit(replacement)
    except Exception as exc:
        progress['errorCleanupUnresolved'] = _safe_error(exc)


def _scheduler_process(pipe):
    from runtime_candidate.transport import CandidateClient
    from .actors import request

    with closing(pipe):
        try:
            endpoint, scope, credential = pipe.recv()
            assignment = request(CandidateClient(*endpoint), 'worker_claim', credential, **scope, worker='worker',
                                 expected_run_version=1)
            body = dict(scope, **{key: assignment[key] for key in ('assignment', 'fence', 'lease_token')})
            pipe.send(('claimed', body))
        except Exception as exc:
            pipe.send(('failure', {'error': _safe_error(exc)}))


def _controlled_coordinator(pipe):
    from runtime_candidate.application import Application
    from runtime_candidate.transport import CandidateClient
    from .actors import request
    from .controller import Controller, PROFILE
    from .profile_unit import PinnedOriginal
    from spikes.s4f.unit import Unit

    progress = {'coordinatorPid': os.getpid()}
    with closing(pipe):
        try:
            schema, state_root, endpoint, scope, body, worker, mode, window, workspace = pipe.recv()
            client = CandidateClient(*endpoint)
            admission = request(client, 'worker_admit', worker, **body)
            require(admission['manifest']['checkRegistry'] == PROFILE and admission['manifest']['inputHashes'] == {}, 'E_PROFILE')
            with closing(Application(schema, state_root)) as app:
                controller = Controller(app)
                try:
                    with closing(Unit('original', workspace)) as original:
                        try:
                            if pipe.poll():
                                require(pipe.recv() == ('abort', None), 'E_CHANNEL')
                                raise Error('E_PARENT_ABORT')
                            armed = controller.arm(worker, body, admission, original)
                            resource = controller.fire(worker, body, admission, original, armed, window=window)
                            progress['original'] = _resource_record(resource)
                            progress['original']['consumedIntentPin'] = armed.pin
                            progress['duplicateAdmission'] = _denial_request(client, 'worker_admit', worker, body, 'E_CONFLICT')
                            progress['duplicateFire'] = _decline_second_fire(controller, worker, body, admission, original, armed)
                            pipe.send(('barrier', {'resource': progress['original'], 'relayPid': original.process.pid,
                                                   'coordinatorPid': os.getpid(), 'duplicateAdmission': 'E_CONFLICT',
                                                   'admissionJobId': admission['jobId'], 'effectNonce': admission['effectNonce'],
                                                   'qaInputPins': admission['manifest']['inputHashes']}))
                            progress['monitor'] = _monitor(pipe, client, worker, body, original, resource, workspace)
                            recovery, progress['authorityLoss'] = controller.fence(resource, original, worker)
                            if original.process.poll() is None:
                                progress['originalKill'] = original.kill_original()
                            progress['originalAbsence'] = PinnedOriginal(resource).absence()
                        finally:
                            progress['originalRelay'] = _closed_unit(original)
                    recovery, pair = _finish_recovery(controller, recovery, scope, mode, workspace, progress)
                except Exception:
                    _teardown_after_error(controller, scope, workspace, progress)
                    raise
            pipe.send(('recovered', (progress, recovery, pair)))
        except Exception as exc:
            pipe.send(('failure', {'error': _safe_error(exc), 'progress': progress}))


def _decline_second_fire(controller, worker, body, admission, original, armed):
    from .fixture import deny
    size = Path(original.output_log.name).stat().st_size
    denied = deny(lambda: controller.fire(worker, body, admission, original, armed), 'E_ONE_USE')
    require(Path(original.output_log.name).stat().st_size == size, 'E_PREMATURE_IO')
    return denied


def _rebuild_coordinator(pipe):
    from runtime_candidate.application import Application
    from .controller import Controller
    from .profile_unit import PinnedOriginal

    progress = {'coordinatorPid': os.getpid(), 'rebuildInputs': ['schema', 'stateRoot', 'project', 'runId']}
    with closing(pipe):
        try:
            schema, state_root, project, run_id = pipe.recv()
            scope = {'project': project, 'run_id': run_id}
            with closing(Application(schema, state_root)) as app:
                controller = Controller(app)
                resource, existing = controller.rebuild(project, run_id)
                require(existing is None and resource.observed is not None, 'E_REBUILD')
                progress['original'] = _resource_record(resource)
                original = PinnedOriginal(resource)
                try:
                    progress['originalAbsence'] = original.absence()
                except RuntimeError:
                    progress['originalAbsence'] = original.kill_original()
                recovery, progress['authorityLoss'] = controller.fence(resource, None, None)
                recovery, pair = _finish_recovery(controller, recovery, scope, 'restart', state_root.parent, progress)
            pipe.send(('recovered', (progress, recovery, pair)))
        except Exception as exc:
            pipe.send(('failure', {'error': _safe_error(exc), 'progress': progress}))


def _receive(owner, event, progress, timeout=90):
    require(owner.pipe.poll(timeout), 'E_CHANNEL')
    actual, value = owner.pipe.recv()
    if actual == 'failure':
        progress['coordinatorFailure'] = value
        raise Error('E_COORDINATOR')
    require(actual == event, 'E_CHANNEL')
    return value


@contextmanager
def _supervised_coordinator(arguments, progress):
    from .actors import actor

    with actor(_controlled_coordinator, arguments) as owner:
        try:
            yield owner
        except Exception:
            if owner.process.is_alive():
                try:
                    owner.send('abort')
                    deadline = time.monotonic() + 75
                    while time.monotonic() < deadline:
                        if not owner.pipe.poll(5):
                            if not owner.process.is_alive():
                                break
                            continue
                        event, value = owner.pipe.recv()
                        if event in ('failure', 'recovered'):
                            if event == 'recovered':
                                value = value[0]  # The private collector pair cannot be acted on here.
                            progress['coordinatorAbort'] = value
                            progress['coordinatorAbortExit'] = owner.join()
                            break
                    if 'coordinatorAbortExit' not in progress:
                        progress['coordinatorAbortUnconfirmed'] = True
                except Exception as exc:
                    progress['coordinatorAbortError'] = _safe_error(exc)
            raise


@contextmanager
def _relay_handle(pid):
    """Hold the original Windows process object across coordinator termination."""
    from ctypes import wintypes

    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel.CloseHandle.restype = wintypes.BOOL
    handle = kernel.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE only
    require(handle, 'E_RELAY')
    try:
        require(kernel.WaitForSingleObject(handle, 0) == 258, 'E_RELAY')
        yield lambda: kernel.WaitForSingleObject(handle, 12000) == 0
    finally:
        require(kernel.CloseHandle(handle), 'E_RELAY')


def _restart(fixture, owner, barrier, progress):
    from .actors import actor
    from .controller import Controller

    keys = ('project', 'run_id')
    with closing(fixture.factory()) as app:
        expected, prior = Controller(app).rebuild(*(fixture.scope[key] for key in keys))
        original = _resource_record(expected)
    require(prior is None and all(barrier['resource'][key] == value for key, value in original.items()), 'E_REBUILD')
    with _relay_handle(barrier['relayPid']) as relay_exited:
        owner.process.terminate()
        owner.process.join(12)
        require(not owner.process.is_alive() and owner.process.exitcode not in (0, None), 'E_ACTOR_EXIT')
        progress['terminatedCoordinator'] = {'pid': owner.process.pid, 'exitCode': owner.process.exitcode}
        with actor(_rebuild_coordinator, (fixture.schema, fixture.state_root, *(fixture.scope[key] for key in keys))) as replacement:
            result = _receive(replacement, 'recovered', progress)
            progress['replacementCoordinatorExit'] = replacement.join()
        require(relay_exited(), 'E_RELAY_REMAINS')
    require(result[0]['original'] == original and result[0]['coordinatorPid'] != barrier['coordinatorPid'], 'E_REBUILD')
    progress['originalRelayExitObserved'] = {'pid': barrier['relayPid'], 'terminated': True}
    return result


def _collector_response(collector, body):
    collector.send('collect', body)
    return collector.receive('collector_response')


def _read_graph(fixture, *, authority_fault=False):
    with closing(fixture.factory()) as app:
        return _db_state(app, fixture.scope, authority_fault=authority_fault)


def _cancel(fixture, version):
    outcome = fixture.request('run_cancel', fixture.admin, **fixture.scope, key='cancel_interruption',
                              grant=fixture.start['grant'], expected_version=version)
    require(outcome['state'] == 'stopping' and outcome['incidentOpen'] is True, 'E_CANCEL_EARLY')
    return outcome


def _unheld_pair(fixture, profile):
    return {'execution': {'mode': 'executed_fixture', 'kind': 'cleanup_only', 'profile': profile,
                          'inputDigest': fixture.input_digest, 'recordSha256': '0' * 64},
            'cleanup': {'containerRemoved': True, 'processesNotLive': True, 'cgroupEmpty': True,
                        'resourceIdentity': {}}}


def _collect(fixture, collector, original_body, recovery, pair, mode, progress):
    from .controller import collection_body

    resource = recovery.resource
    if mode in ('newer_head', 'unknown_head'):
        # An unacknowledged candidate envelope. The collector is genuinely enrolled.
        pair = _unheld_pair(fixture, resource.profile)
    body = collection_body(recovery, pair)
    unknown = mode == 'unknown_head'
    graph = _read_graph(fixture, authority_fault=unknown)
    if mode in ('newer_head', 'unknown_head', 'lost_ack'):
        code = 'E_STALE' if mode == 'newer_head' else 'E_UNRESOLVED'
        require(_collector_response(collector, body) == {'denied': code}, 'E_COLLECTOR')
        progress['collectorWithoutObservation'] = code
        _no_acceptance(graph, 'unresolved')
        require(_read_graph(fixture, authority_fault=unknown) == graph, 'E_GRAPH')
        progress['finalGraph'] = graph
        return

    _no_acceptance(graph, 'unresolved', observation=True)
    # Reuse the original, valid same-project worker lease to prove that it cannot publish.
    progress['priorWorkerPublish'] = _denial_request(fixture.client, 'worker_submit', fixture.services['worker'],
                                                    dict(original_body, assessment_digest='0' * 64), 'E_STALE', 'E_AUTH')
    require(_collector_response(collector, dict(body, fence=resource.binding['fence'])) == {'denied': 'E_STALE'}, 'E_COLLECTOR')
    changed_record = dict(body['execution'], recordSha256='0' * 64)
    changed_resource = dict(body['cleanup'], resourceIdentity={})
    for field, value in (('execution', changed_record), ('cleanup', changed_resource)):
        require(_collector_response(collector, dict(body, **{field: value})) == {'denied': 'E_UNRESOLVED'}, 'E_COLLECTOR')
    progress['collectorNegatives'] = {'priorFence': 'E_STALE', 'changedProof': 'E_UNRESOLVED',
                                      'changedResource': 'E_UNRESOLVED'}
    progress['wrongProjectCollector'] = _denial_request(fixture.client, 'collector_record',
                                                       fixture.services['otherCollector'], body, 'E_AUTH')
    if mode == 'cancel':
        progress['wrongAudienceWorker'] = _denial_request(fixture.client, 'collector_record',
                                                          fixture.services['worker'], body, 'E_AUTH')
    require(_read_graph(fixture) == graph, 'E_GRAPH')
    result = _collector_response(collector, body)
    require(result == {'result': {'accepted': False, 'cleanupOnly': True,
                                  'executionDigest': digest(body['execution'])}}, 'E_COLLECTOR')
    final = _read_graph(fixture)
    _empty_progress(final)
    terminal = 'cancelled' if mode == 'cancel' else 'failed'
    require(final['state'] == terminal and final['incident'] is False and len(final['executions']) == 1
            and final['fence'] == recovery.current_fence, 'E_GRAPH')
    execution, = final['executions']
    require(execution['work_accepted'] is False and (execution['assignment'], execution['fence'],
            execution['effect_nonce'], execution['record_digest'], execution['collector']) ==
            (body['assignment'], body['fence'], body['effect_nonce'], digest(body['execution']), 'collector'), 'E_COLLECTOR')
    progress.update(independentCollector=result['result'], finalGraph=final)


def _controlled_case(workspace, certificate, key, forbidden, mode, window, lease, budget, progress):
    from .actors import actor, collector_process, ui_process
    from .fixture import fixture

    with fixture(workspace, certificate, key, forbidden, lease=lease, budget=budget) as ctx:
        progress['fixture'] = {'schema': ctx.schema, **ctx.scope, 'leaseSeconds': lease, 'runSeconds': budget}
        with actor(ui_process, (ctx.endpoint, ctx.admin, ctx.start)) as ui:
            started = ui.receive('started')
            require(started['result']['state'] == 'queued' and started['pid'] == ui.process.pid, 'E_START')
            with actor(_scheduler_process, (ctx.endpoint, ctx.scope, ctx.services['scheduler'])) as scheduler:
                body = _receive(scheduler, 'claimed', progress)
                forbidden.append(body['lease_token'].encode())
                progress['schedulerExit'] = scheduler.join()
            args = (ctx.schema, ctx.state_root, ctx.endpoint, ctx.scope, body,
                    ctx.services['worker'], mode, window, workspace)
            with _supervised_coordinator(args, progress) as owner:
                barrier = _receive(owner, 'barrier', progress)
                progress['barrier'] = barrier
                require(owner.process.is_alive() and barrier['coordinatorPid'] == owner.process.pid != started['pid'], 'E_ACTOR')
                if mode == 'cancel' and window == 'after_identity':
                    alternate = ctx.request('service_enroll', ctx.admin, service='workerOther', kind='worker',
                                            projects=[ctx.scope['project']])['credential']
                    forbidden.append(alternate.encode())
                    graph = _read_graph(ctx)
                    progress['wrongWorker'] = _denial_request(ctx.client, 'worker_admit', alternate, body, 'E_STALE')
                    require(_read_graph(ctx) == graph, 'E_GRAPH')
                ui.send('exit')
                progress['uiExit'] = ui.join()
                if mode in ('cancel', 'restart'):
                    owner.send('inspect')
                    live = _receive(owner, 'inspected', progress)
                    require(owner.process.is_alive() and live['coordinatorPid'] == barrier['coordinatorPid'], 'E_ACTOR')
                    observed = live['resource']
                    if window == 'before_create':
                        require(observed is None and barrier['resource']['durableResource'] is None, 'E_WINDOW')
                    else:
                        require(observed is not None and observed['running'] is True and len(observed['processes']) == 3,
                                'E_RESOURCE_LIVE')
                        durable = barrier['resource']['durableResource']
                        require(observed == durable if window == 'after_identity' else durable is None, 'E_WINDOW')
                    progress['liveAfterUiExit'] = live
                with actor(collector_process, (ctx.endpoint, ctx.services['collector'])) as collector:
                    progress['collector'] = collector.receive('ready')
                    require(progress['collector']['pid'] not in (started['pid'], owner.process.pid), 'E_ACTOR')
                    if mode == 'cancel':
                        graph = _read_graph(ctx)
                        _no_acceptance(graph, 'collecting')
                        unheld = dict(ctx.scope, assignment=body['assignment'], fence=body['fence'],
                                      effect_nonce=barrier['effectNonce'], **_unheld_pair(ctx, barrier['resource']['profile']))
                        require(_collector_response(collector, unheld) == {'denied': 'E_UNRESOLVED'}, 'E_COLLECTOR')
                        require(_read_graph(ctx) == graph, 'E_GRAPH')
                        progress['liveCollectorWithoutObservation'] = 'E_UNRESOLVED'
                        progress['userCancellation'] = _cancel(ctx, graph['version'])
                    elif mode == 'revoke':
                        require(ctx.request('service_revoke', ctx.admin, service='worker') == {'revoked': True}, 'E_REVOKE')
                    elif mode in ('unit', 'newer_head', 'unknown_head', 'lost_ack'):
                        owner.send('kill_original')
                    if mode == 'restart':
                        progress['coordinator'], recovery, pair = _restart(ctx, owner, barrier, progress)
                    else:
                        progress['coordinator'], recovery, pair = _receive(owner, 'recovered', progress, timeout=115)
                        progress['coordinatorExit'] = owner.join()
                    cause = {'cancel': 'cancelled_by_user', 'revoke': 'worker_authority_lost',
                             'lease': 'lease_expired', 'budget': 'run_budget_expired'}.get(mode, 'original_supervisor_exited')
                    loss = progress['coordinator']['authorityLoss']
                    require(loss['reason'] == cause, 'E_LOSS')
                    if mode == 'lease':
                        require(datetime.fromisoformat(loss['leaseAt']) <= datetime.fromisoformat(loss['at'])
                                < datetime.fromisoformat(loss['runBudgetAt']), 'E_CLOCK')
                    elif mode == 'budget':
                        require(datetime.fromisoformat(loss['runBudgetAt']) <= datetime.fromisoformat(loss['at']), 'E_CLOCK')
                    if window == 'before_create':
                        require(progress['coordinator']['cleanup']['removedContainerId'] is None, 'E_WINDOW')
                    elif window == 'after_start':
                        require(progress['coordinator']['cleanup']['removedContainerId'] == observed['containerId'], 'E_WINDOW')
                    _collect(ctx, collector, body, recovery, pair, mode, progress)
                    collector.send('exit')
                    progress['collectorExit'] = collector.join()


def _run_cases(workspace, certificate, key, forbidden, checks):
    from .qa_cases import run_case

    for name, mode, window, lease, budget in CASES:
        row = checks[name]
        row['status'] = 'RUNNING'
        location = workspace / name
        location.mkdir()
        try:
            _controlled_case(location, certificate, key, forbidden, mode, window, lease, budget, row)
        except Exception as exc:
            row.update(status='ERROR', error=_safe_error(exc))
            return
        else:
            row['status'] = 'PASS'
    for name in QA_CASES:
        row = checks[name]
        row['status'] = 'RUNNING'
        location = workspace / name
        location.mkdir()
        try:
            row.update(run_case(location, certificate, key, forbidden, case=name))
        except Exception as exc:
            row.update(status='ERROR', error=_safe_error(exc))
            return
        else:
            row['status'] = 'PASS'


def _has_secret(data, forbidden):
    for secret in forbidden:
        if not secret:
            continue
        hex_value = secret.hex().encode()
        forms = (secret, base64.b64encode(secret).rstrip(b'='), base64.urlsafe_b64encode(secret).rstrip(b'='),
                 hex_value, hex_value.upper())
        if any(form in data for form in forms):
            return True
    return False


def _db_status(local, config):
    try:
        local.command('pg_ctl', '-D', config['data'], 'status')
    except subprocess.CalledProcessError as exc:
        return exc.returncode
    return 0


@contextmanager
def _campaign_lock(cache):
    import msvcrt

    with (cache / '.current-campaign.lock').open('a+b') as lock:
        lock.seek(0)
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        try:
            yield
        finally:
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


def main():
    require(len(sys.argv) == 2 and re.fullmatch(r'[A-Za-z0-9_-]{1,80}\.json', sys.argv[1]), 'E_OUTPUT')
    directory = ROOT / 'docs/m50-worker-results'
    destination = directory / sys.argv[1]
    cache = ROOT / '.cache/s6/m50-worker'
    require(directory.resolve() == directory and cache.resolve() == cache and not destination.exists(), 'E_OUTPUT')
    cache.mkdir(parents=True, exist_ok=True)
    workspace = cache / destination.stem
    workspace.mkdir(exist_ok=False)
    forbidden = []
    evidence = {'version': 'm50-worker-1.0.0', 'applicationVersion': VERSION, 'classification': 'synthetic-only',
                'status': 'ERROR', 'databaseStopped': None, 'startedAt': datetime.now(timezone.utc).isoformat(),
                'inputsBefore': source_pins(), 'checks': {name: {'status': 'PENDING'}
                    for name in [case[0] for case in CASES] + list(QA_CASES)}}
    try:
        from runtime_candidate.database import stop_database
        from spikes.s2 import local
        from spikes.s6b.preflight_b import inventory as identity_inventory
        local.clean_environment()
        # The retained maintenance helper resolves the same pinned local module by bare name.
        sys.path.insert(0, str(ROOT / 'spikes/s2'))
        with _campaign_lock(cache):
            evidence['databaseInventory'] = local.inventory()
            evidence['identityInventory'] = identity_inventory()
            require(evidence['databaseInventory']['toolchainReady'] and evidence['identityInventory']['ready'], 'E_PREREQUISITES')
            config = local.read_config(False)
            evidence['databaseStatusBefore'] = _db_status(local, config)
            require(evidence['databaseStatusBefore'] == 3, 'E_DB_NOT_STOPPED')
            try:
                local.start()
                from runtime_candidate.test_transport import make_test_certificate
                cert, key = make_test_certificate(workspace)
                private_key = key.read_bytes()
                forbidden.extend((private_key, *(line for line in private_key.splitlines() if not line.startswith(b'-----'))))
                _run_cases(workspace, cert, key, forbidden, evidence['checks'])
            finally:
                try:
                    code = _db_status(local, config)
                    if code == 0:
                        evidence['databaseStopObservation'] = stop_database()
                        code = _db_status(local, config)
                    evidence['databaseStatusAfter'] = code
                    evidence['databaseStopped'] = code == 3
                    require(evidence['databaseStopped'], 'E_DB_NOT_STOPPED')
                except Exception as exc:
                    evidence['databaseStopped'] = False
                    evidence['databaseStopError'] = _safe_error(exc)
                    raise
    except Exception as exc:
        evidence['error'] = _safe_error(exc)
    evidence['inputsAfter'] = source_pins()
    evidence['inputsStable'] = evidence['inputsBefore'] == evidence['inputsAfter']
    evidence['finishedAt'] = datetime.now(timezone.utc).isoformat()
    diagnostics = sorted(path for path in workspace.rglob('*') if path.suffix in ('.stderr', '.stdout', '.log')
                         or path.name in ('worker.stdout.json', 'supervisor.json', 'error.txt'))
    evidence['diagnosticsScanned'] = len(diagnostics)
    evidence['credentialScanPassed'] = not any(_has_secret(path.read_bytes(), forbidden) for path in diagnostics)
    if (evidence['databaseStopped'] is True and evidence['inputsStable'] and evidence['credentialScanPassed']
            and 'error' not in evidence and all(row['status'] == 'PASS' for row in evidence['checks'].values())):
        evidence['status'] = 'PASS'
    raw = canonical(evidence)
    require(not _has_secret(raw, forbidden), 'E_EVIDENCE_SECRET')
    directory.mkdir(exist_ok=True)
    with destination.open('xb') as stream:
        stream.write(raw + b'\n')
    print(canonical({'status': evidence['status'], 'databaseStopped': evidence['databaseStopped'],
                     'checks': {name: row['status'] for name, row in evidence['checks'].items()}}).decode())
    return 0 if evidence['status'] == 'PASS' else 2


if __name__ == '__main__':
    raise SystemExit(main())
