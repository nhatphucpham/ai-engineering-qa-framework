"""Linux-only VF1 adapter for the independently pinned S4-F recovery journal."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from runtime_candidate.linux_input_guard import install_held_reader, load_worker
from spikes.s4f import linux_supervisor as s4f


PROFILE = 'vf1-fixed-1.0.0'
vf1 = load_worker()
check = s4f.check


def inspect_qa(engine, ctx, binding, cid):
    labels = s4f.labeled(binding)
    row, = json.loads(engine.command(['inspect', '--type=container', cid]).stdout)
    cfg, host, state = row['Config'], row['HostConfig'], row['State']
    check(row['Id'] == cid and row['Name'].lstrip('/') == binding['container_name']
          and row['Image'].removeprefix('sha256:') == ctx['image'].removeprefix('sha256:')
          and all(cfg['Labels'].get(key) == value for key, value in labels.items())
          and cfg['Cmd'] == vf1.CONTAINER_COMMAND and cfg['User'] == '1000:1000'
          and host['ReadonlyRootfs'] is True and host['Privileged'] is False and host['NetworkMode'] == 'none'
          and host['CgroupParent'] == str(engine.container_parent).removeprefix('/sys/fs/cgroup'), 'E_CONTAINER_CONFIG')
    mounts = {m['Destination']: (m['Source'], m['RW']) for m in row['Mounts'] if m['Type'] == 'bind'}
    check(mounts == {'/input': (str(engine.base / 'input'), False),
                     '/output': (str(engine.base / 'output'), True)}, 'E_MOUNTS')
    result = {'containerId': cid, 'status': state['Status'], 'running': state['Running'], 'initPid': state['Pid'],
              'boot': ctx['boot'], 'processes': {}, 'cgroup': None}
    if result['running']:
        live = {}
        attached = not hasattr(engine, 'owned')
        if attached:
            engine.owned = [cid]  # Only after full enumeration and exact immutable inspection.
        try:
            vf1.observe_live(engine, cid, binding['container_name'], labels, live)
        finally:
            if attached:
                del engine.owned
        processes = {pid: {'pid': int(pid), 'startTime': item['startTime']}
                     for pid, item in live['processesBefore'].items()}
        check(len(processes) == 1 and str(result['initPid']) in processes, 'E_PROCESS')
        result.update(processes=processes, cgroup=live['containerCgroup'])
    else:
        check(result['initPid'] == 0 and result['status'] in ('configured', 'created', 'stopped', 'exited'), 'E_NOT_STOPPED')
    return result


class Supervisor(s4f.Supervisor):
    def __init__(self, ctx, engine, role, *, image=None, pins=None):
        super().__init__(ctx, engine, role)
        self.image = image
        self.pins = pins
        self.started_at = None
        self.execution = None
        self.release = None

    def execute(self, req):
        op, binding = req['op'], req['binding']
        if self.role != 'original' or op not in ('fire', 'release', 'poll', 'finish'):
            prior = super().execute(req)
            if self.role == 'observer' and op == 'observe':
                output = self.engine.base / 'output'
                prior['releaseBarrierClosed'] = not (output / '.allow-start').exists() and not (output / 'result.json').exists()
            return prior
        s4f.binding_ok(binding, self.ctx)
        check(binding['run_id'] == self.ctx['admissionRunId'], 'E_BINDING')
        state = self.state(req)
        if op == 'fire':
            check(not self.fired and state['phase'] == 'consumed' and req['window'] == 'after_identity'
                  and not s4f.listing(self.engine), 'E_ONE_USE')
            self.fired = True
            self.started_at = datetime.now(timezone.utc).isoformat()
            name, labels = binding['container_name'], s4f.labeled(binding)
            cid = self.engine.launch_fixed(name, labels)
            state['resource'] = self.inspect(state)
            state['phase'] = 'identified'
            self.execution = {'containerId': cid, 'containerName': name, 'labels': labels, 'command': vf1.CONTAINER_COMMAND}
            vf1.observe_live(self.engine, cid, name, labels, self.execution)
            return {'barrier': 'after_identity', 'journalPin': self.save(state), 'resource': state['resource'],
                    'releaseBarrier': 'before_fixed_checks'}
        check(self.fired and state['phase'] == 'identified' and self.execution is not None, 'E_ONE_USE')
        if op == 'release':
            check(self.release is None and self.inspect(state) == state['resource']
                  and state['resource']['running'], 'E_NOT_RUNNING')
            release = {'operation': 'release_fixed_checks', 'journalPin': req['journalPin'],
                       'contextPin': s4f.digest(self.ctx), 'binding': binding}
            s4f.atomic(self.engine.base / 's4f-qa-release.json', release)
            output_fd = os.open(self.engine.base / 'output', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
            try:
                marker = os.open('.allow-start', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC,
                                 mode=0o400, dir_fd=output_fd)
                os.close(marker)
                os.fsync(output_fd)
            finally:
                os.close(output_fd)
            self.release = s4f.digest(release)
            return {'releasePin': self.release}
        check(self.release is not None and req['releasePin'] == self.release
              and s4f.digest(s4f.load(self.engine.base / 's4f-qa-release.json')) == self.release, 'E_JOURNAL')
        status = vf1.owned_inspect(self.engine, self.execution['containerId'],
                                   binding['container_name'], self.execution['labels'])['State']
        if op == 'poll':
            return {'running': status['Running'], 'pid': status['Pid']}
        check(status['Running'] is False and status['Pid'] == 0 and status['ExitCode'] == 0, 'E_WRAPPER_EXIT')
        return self.finish(state)

    def finish(self, state):
        engine, execution = self.engine, self.execution
        name, labels = (execution[key] for key in ('containerName', 'labels'))
        run_id, job_id = self.ctx['admissionRunId'], self.ctx['admissionJobId']
        output_fd = os.open(engine.base / 'output', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            execution.update(exitCode=0, containerStoppedPidZero=True)
            execution.update(vf1.collect_result(output_fd, run_id, job_id))
        finally:
            os.close(output_fd)
        cleanup = {}
        vf1.cleanup_job(engine, name, labels, execution, cleanup)
        check(cleanup == {'containerRemoved': True, 'processesNotLive': True, 'cgroupEmpty': True}, 'E_CLEANUP')
        record = {'workerVersion': vf1.WORKER_VERSION, 'runId': run_id, 'jobId': job_id, 'status': 'complete',
                  'execution': execution, 'cleanup': cleanup, 'startedAt': self.started_at,
                  'finishedAt': datetime.now(timezone.utc).isoformat(), 'image': self.image,
                  'inputHashes': self.pins, 'privateCache': str(engine.base),
                  'engine': {'rootless': engine.info['host']['security']['rootless'],
                             'podmanVersion': engine.info['version']['Version'], 'delegatedParent': str(engine.parent)}}
        proof = {'operation': 'qa_success_cleanup', 'rawRecordSha256': s4f.digest(record)}
        state.update(phase='qa_completed', proof=proof)
        return {'journalPin': self.save(state), 'record': record}


def main(role, unit):
    check(role in ('original', 'replacement', 'observer'), 'E_ROLE')
    request = json.loads(sys.stdin.readline())
    # The unmodified replacement calls this module-local profile's inspection via
    # the S4-F namespace only inside this dedicated process.
    s4f.inspect_resource = inspect_qa
    image = pins = None
    if role == 'original':
        check(set(request) == {'staging', 'runId', 'jobId', 'inputHashes'}
              and all(vf1.IDENTIFIER.fullmatch(request[key]) for key in ('runId', 'jobId')), 'E_INPUT')
        install_held_reader(vf1, request['inputHashes'])
        payloads, pins = vf1.read_staging(request['staging'], request['runId'], request['jobId'])
        engine = vf1.VF1Engine()
        image = engine.build_image()
        vf1.stage_private(engine, payloads)
        ctx = dict(s4f.context(engine, unit), profile=PROFILE, admissionRunId=request['runId'],
                   admissionJobId=request['jobId'], heldInputPinsSha256=s4f.digest(pins))
        s4f.atomic(engine.base / 's4f-context.json', ctx)
    else:
        ctx = request['context']
        check(ctx['profile'] == PROFILE and s4f.digest(ctx) == request['contextPin'], 'E_CONTEXT')
        engine = s4f.attach(ctx)
        if role == 'replacement':
            s4f.original_absent(ctx)
    supervisor = Supervisor(ctx, engine, role, image=image, pins=pins)
    print(json.dumps({'ready': True, 'context': ctx, 'contextPin': s4f.digest(ctx), 'image': image,
                      'process': s4f.process(os.getpid()), 'unit': unit}), flush=True)
    for line in sys.stdin:
        try:
            result = supervisor.execute(json.loads(line))
            print(json.dumps({'ok': True, 'result': result}), flush=True)
        except (ValueError, KeyError, OSError, RuntimeError, StopIteration) as exc:
            print(json.dumps({'ok': False, 'code': error_code(exc)}), flush=True)


def error_code(exc):
    import traceback
    traceback.print_exc(file=sys.stderr)
    code = str(exc).partition(':')[0]
    return code if re.fullmatch(r'E_[A-Z_]+', code) else 'E_OBSERVATION'


if __name__ == '__main__':
    try:
        main(*sys.argv[1:])
    except Exception as exc:
        print(json.dumps({'ready': False, 'code': error_code(exc)}), flush=True)
        raise
