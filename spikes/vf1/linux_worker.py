"""Single-job, private Linux supervisor for the frozen VF1 synthetic fixture."""

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import re
import stat
import subprocess
import sys
import tarfile
import uuid


ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / relative) for relative in ('spikes/vf1', 'spikes/s4', 'spikes/s4b')]
from collector import Blocked, PrivateCollector
from engine import RootlessEngine
from run_engine import pid_state
from test_worker import OUTCOMES, RESULT_VERSION, TEST_IDS, TRACE_LIMIT, counts_for


WORKER_VERSION = 'vf1-linux-worker-1.0.0'
STAGING_CACHE = ROOT / '.cache/s6/vf1'
CASE = ROOT / 'examples/mock/06-filter-pagination'
CASE_FILES = ('requirements.md', 'head/api.py', 'head/data.py', 'head/service.py', 'head/ui.py',
              'tests/test_baseline.py', 'tests/test_historical.py', 'expected/test_probe.py')
TRUSTED_INPUTS = {'case/' + name: CASE / name for name in CASE_FILES}
TRUSTED_INPUTS['test_worker.py'] = ROOT / 'spikes/vf1/test_worker.py'
IDENTIFIER = re.compile('[A-Za-z0-9_-]{1,64}')
SHA256 = re.compile('[a-f0-9]{64}')
PYTHON = Path('/usr/bin/python3')
STDLIB = Path('/usr/lib/python3.12')
TIMEOUT_SECONDS = 30
CONTAINER_COMMAND = [str(PYTHON), '-I', '-S', '-B', '/input/test_worker.py']
CGROUP_LIMITS = {'memory.max': str(256 * 1024 * 1024), 'pids.max': '64', 'cpu.max': '50000 100000'}


class WorkerError(RuntimeError):
    pass


def require(condition, code):
    if not condition:
        raise WorkerError(code)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def strict_json(data):
    def object_from_pairs(pairs):
        value = {}
        for key, item in pairs:
            require(key not in value, 'E_DUPLICATE_JSON_KEY')
            value[key] = item
        return value

    def invalid_constant(_token):
        raise WorkerError('E_NONFINITE_JSON')

    return json.loads(data.decode('utf-8'), object_pairs_hook=object_from_pairs, parse_constant=invalid_constant)


@contextmanager
def private_collector(fd, run_id, job_id, **limits):
    info = os.fstat(fd)
    scope = {'projectId': 'mock-06-vf1', 'runId': run_id, 'assignmentId': job_id, 'attempt': 1, 'fence': 1}
    collector = PrivateCollector(fd, (info.st_dev, info.st_ino), scope, **limits)
    try:
        yield collector
    finally:
        collector.close()


def read_staging(path_value, run_id, job_id):
    path = Path(path_value)
    require(path.is_absolute() and path != STAGING_CACHE and path.is_relative_to(STAGING_CACHE)
            and '..' not in path.parts, 'E_INPUT_SCOPE')
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    fd = os.open(ROOT, flags)
    try:
        for part in path.relative_to(ROOT).parts:
            child = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = child
        with private_collector(fd, run_id, job_id, max_bytes=65536, max_files=len(TRUSTED_INPUTS) + 1,
                               max_total=512 * 1024) as collector:
            marker = strict_json(collector.collect_private('marker.json').private_bytes())
            require(type(marker) is dict and set(marker) == {'kind', 'runId', 'jobId', 'inputHashes'}
                    and marker['kind'] == 'vf1-input-v1' and marker['runId'] == run_id
                    and marker['jobId'] == job_id, 'E_INPUT_MARKER')
            hashes = marker['inputHashes']
            require(type(hashes) is dict and set(hashes) == set(TRUSTED_INPUTS)
                    and all(type(value) is str and SHA256.fullmatch(value) for value in hashes.values()),
                    'E_INPUT_MANIFEST')
            payloads = {}
            for name, trusted_file in TRUSTED_INPUTS.items():
                blob = collector.collect_private(name)
                require(blob.manifest['sha256'] == hashes[name] == sha256(trusted_file.read_bytes()), 'E_INPUT_HASH')
                payloads[name] = blob.private_bytes()
            return payloads, hashes
    finally:
        os.close(fd)


def own_delegation():
    member = next(line[3:] for line in Path('/proc/self/cgroup').read_text().splitlines() if line.startswith('0::'))
    current = Path(member)
    require(os.getuid() == 1000 and current.name == 'supervisor'
            and re.fullmatch(r'qa-s4-vf1-[A-Za-z0-9_-]+\.service', current.parent.name), 'E_VF1_DELEGATION')


def local_libraries(path):
    # The dependency probe only inspects the fixed system interpreter and stdlib ELF extensions.
    output = subprocess.run(['/usr/bin/ldd', str(path)], text=True, capture_output=True, check=True, timeout=5,
                            env={'PATH': '/usr/bin:/bin', 'LC_ALL': 'C'}).stdout
    libraries = {}
    for line in output.splitlines():
        line = line.strip()
        if line == 'statically linked' or line.startswith('linux-vdso.so.'):
            continue
        match = re.fullmatch(r'(?:\S+ => )?(/\S+) \(0x[0-9a-f]+\)', line)
        require(match is not None, 'E_SYSTEM_LIBRARY_DISCOVERY')
        alias = Path(match[1])
        require(alias.parts[1] in ('lib', 'lib64', 'usr') and '..' not in alias.parts, 'E_SYSTEM_LIBRARY_PATH')
        source = alias.resolve(strict=True)
        require(source.is_relative_to('/usr/lib') or source.is_relative_to('/usr/lib64'), 'E_SYSTEM_LIBRARY_PATH')
        libraries[alias] = source
    return libraries


def runtime_files():
    interpreter = PYTHON.resolve(strict=True)
    require(interpreter == Path('/usr/bin/python3.12') and STDLIB.resolve(strict=True) == STDLIB
            and (sys.version_info.major, sys.version_info.minor) == (3, 12), 'E_SYSTEM_PYTHON')
    files = {PYTHON: interpreter}
    binaries = [interpreter]
    for directory, subdirs, names in os.walk(STDLIB):
        subdirs[:] = [name for name in subdirs if name not in ('__pycache__', 'site-packages', 'dist-packages')]
        for name in names:
            path = Path(directory) / name
            if path.suffix in ('.py', '.so') and stat.S_ISREG(path.lstat().st_mode):
                files[path] = path
                if path.suffix == '.so':
                    binaries.append(path)
    for path in binaries:
        files.update(local_libraries(path))
    return files


def pack_runtime(archive, files):
    directories = {Path(path) for path in ('/dev', '/etc', '/proc', '/sys', '/tmp', '/input', '/output')}
    for name in files:
        directories.update(parent for parent in name.parents if parent != Path('/'))
    manifest = {}
    with tarfile.open(archive, 'w') as package:
        for directory in sorted(directories):
            entry = tarfile.TarInfo(directory.as_posix().lstrip('/'))
            entry.type = tarfile.DIRTYPE
            entry.mode = 0o1777 if directory == Path('/tmp') else 0o755
            package.addfile(entry)
        for name, source in sorted(files.items()):
            fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
            with os.fdopen(fd, 'rb') as stream:
                info = os.fstat(stream.fileno())
                require(stat.S_ISREG(info.st_mode) and info.st_uid == 0 and info.st_mode & 0o022 == 0,
                        'E_SYSTEM_FILE_OWNER')
                data = stream.read()
            entry = tarfile.TarInfo(name.as_posix().lstrip('/'))
            entry.mode = 0o755 if info.st_mode & 0o111 else 0o644
            entry.size = len(data)
            package.addfile(entry, io.BytesIO(data))
            manifest[name.as_posix()] = {'source': source.as_posix(), 'byteLength': len(data), 'sha256': sha256(data)}
    return manifest


class VF1Engine(RootlessEngine):
    def build_image(self):
        archive = self.base / 'python-rootfs.tar'
        manifest = pack_runtime(archive, runtime_files())
        with archive.open('rb') as stream:
            tar_hash = hashlib.file_digest(stream, 'sha256').hexdigest()
        import_result = self.command(['import', '--change', 'USER 1000:1000', str(archive), 'localhost/qa-vf1-python:1'], timeout=90)
        self.image = import_result.stdout.strip()
        require(re.fullmatch('sha256:[a-f0-9]{64}', self.image), 'E_IMAGE_PIN')
        info = json.loads(self.command(['image', 'inspect', self.image]).stdout)[0]
        require(info['Id'].removeprefix('sha256:') == self.image.removeprefix('sha256:'), 'E_IMAGE_ID')
        return {'imageId': self.image, 'rootfsTarSha256': tar_hash, 'pythonVersion': platform.python_version(),
                'fileManifest': manifest,
                'fileManifestSha256': sha256(json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode())}

    def launch_fixed(self, name, labels):
        args = ['run', '-d', '--pull=never', '--name', name, '--userns=keep-id', '--user=1000:1000',
                '--read-only', '--read-only-tmpfs=false', '--cap-drop=all', '--security-opt=no-new-privileges',
                '--network=none', '--memory=256m', '--memory-swap=256m', '--pids-limit=64', '--cpus=0.5',
                '--timeout=' + str(TIMEOUT_SECONDS), '--log-driver=none', '--workdir=/',
                '--cgroup-parent', str(self.container_parent).removeprefix('/sys/fs/cgroup'),
                '--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=8m,mode=1777',
                '--volume', str(self.base / 'input') + ':/input:ro',
                '--volume', str(self.base / 'output') + ':/output:rw']
        for key, value in labels.items():
            args.extend(('--label', key + '=' + value))
        container = self.command(args + [self.image, *CONTAINER_COMMAND]).stdout.strip()
        require(SHA256.fullmatch(container), 'E_CONTAINER_ID')
        self.owned.append(container)
        return container


def stage_private(engine, payloads):
    for name, payload in payloads.items():
        target = engine.base / 'input' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(payload)
        target.chmod(0o444)


def owned_inspect(engine, container, name, labels):
    info = engine.inspect(container)
    require(info['Id'] == container and info['Name'].lstrip('/') == name
            and info['Image'].removeprefix('sha256:') == engine.image.removeprefix('sha256:')
            and all(info['Config']['Labels'].get(key) == value for key, value in labels.items()), 'E_CONTAINER_SCOPE')
    return info


def observe_live(engine, container, name, labels, execution):
    info = owned_inspect(engine, container, name, labels)
    pid = info['State']['Pid']
    require(info['State']['Running'] is True and type(pid) is int and pid > 1, 'E_NOT_RUNNING')
    group = engine.cgroup(container)
    execution['containerCgroup'] = str(group)
    pids = {int(value) for proc_file in group.rglob('cgroup.procs') for value in proc_file.read_text().split()}
    processes = {str(value): pid_state(value) for value in sorted(pids)}
    require(pid in pids and all(value is not None for value in processes.values()), 'E_PROCESS_IDENTITY')
    execution['processesBefore'] = processes
    execution['initPid'] = pid

    limits = {name: (group / name).read_text().strip() for name in CGROUP_LIMITS}
    require(limits == CGROUP_LIMITS, 'E_CGROUP_LIMITS')
    proc_status = dict(line.split(':', 1) for line in Path(f'/proc/{pid}/status').read_text().splitlines() if ':' in line)
    require(proc_status['Uid'].split() == ['1000'] * 4 and int(proc_status['CapEff'].strip(), 16) == 0
            and proc_status['NoNewPrivs'].strip() == '1', 'E_CONTAINER_PRIVILEGES')
    net_ns = os.readlink(f'/proc/{pid}/ns/net')
    require(info['HostConfig']['NetworkMode'] == 'none' and net_ns != os.readlink('/proc/self/ns/net'), 'E_CONTAINER_NETWORK')
    require(info['HostConfig']['ReadonlyRootfs'] is True and info['HostConfig']['Privileged'] is False, 'E_CONTAINER_ROOTFS')
    mounts = {mount['Destination']: (mount['Source'], mount['RW']) for mount in info['Mounts'] if mount['Type'] == 'bind'}
    require(mounts == {'/input': (str(engine.base / 'input'), False),
                       '/output': (str(engine.base / 'output'), True)}, 'E_CONTAINER_MOUNTS')
    require(pid_state(pid)['startTime'] == processes[str(pid)]['startTime'], 'E_PROCESS_IDENTITY')
    execution['limits'] = {**limits, 'containerTimeoutSeconds': TIMEOUT_SECONDS}
    execution['controls'] = {'hostUid': os.getuid(), 'zeroEffectiveCapabilities': True, 'noNewPrivileges': True,
                             'networkMode': 'none', 'differentNetworkNamespace': True, 'readOnlyRootfs': True,
                             'readOnlyInput': True, 'privateOutput': True}


def collect_result(output_fd, run_id, job_id):
    with private_collector(output_fd, run_id, job_id, max_bytes=192 * 1024, max_files=1) as collector:
        blob = collector.collect_private('result.json')
    result = strict_json(blob.private_bytes())
    require(type(result) is dict and set(result) == {'resultVersion', 'pythonVersion', 'uid', 'counts', 'observations'}
            and result['resultVersion'] == RESULT_VERSION and result['pythonVersion'] == platform.python_version()
            and type(result['uid']) is int and result['uid'] == 1000, 'E_RESULT_IDENTITY')
    observations = result['observations']
    require(type(observations) is list and len(observations) == len(TEST_IDS), 'E_OBSERVATION_COUNT')
    for expected_id, observation in zip(TEST_IDS, observations):
        require(type(observation) is dict and set(observation) == {'testId', 'outcome', 'traceText'}
                and observation['testId'] == expected_id and observation['outcome'] in OUTCOMES
                and type(observation['traceText']) is str and len(observation['traceText']) <= TRACE_LIMIT
                and (observation['outcome'] != 'pass' or observation['traceText'] == ''), 'E_OBSERVATION')
    counts = result['counts']
    require(type(counts) is dict and all(type(count) is int for count in counts.values())
            and counts == counts_for(observations), 'E_RESULT_COUNTS')
    return {'observations': observations, 'counts': counts, 'containerUid': result['uid'],
            'collector': blob.manifest, 'resultVersion': result['resultVersion']}


def listing(engine):
    rows = json.loads(engine.command(['ps', '--all', '--no-trunc', '--format=json']).stdout)
    require(type(rows) is list, 'E_CONTAINER_LIST')
    for row in rows:
        require(type(row) is dict and type(row.get('Names')) is list
                and type(row.get('Id', row.get('ID'))) is str and SHA256.fullmatch(row.get('Id', row.get('ID'))),
                'E_CONTAINER_LIST')
    return rows


def group_empty(group):
    try:
        events = dict(line.split() for line in (group / 'cgroup.events').read_text().splitlines())
        return events['populated'] == '0'
    except FileNotFoundError:
        return not group.exists()


def original_processes_gone(processes):
    for pid, original in processes.items():
        current = pid_state(int(pid))
        if current is not None and current['state'] != 'Z' and current['startTime'] == original['startTime']:
            return False
    return True


def cleanup_job(engine, name, labels, execution, cleanup):
    rows = listing(engine)
    if rows:
        require(len(rows) == 1 and name in rows[0]['Names'], 'E_CLEANUP_UNKNOWN_CONTAINER')
        container = rows[0].get('Id', rows[0].get('ID'))
        require(execution.get('containerId', container) == container, 'E_CLEANUP_CONTAINER_ID')
        if container not in engine.owned:
            engine.owned.append(container)
        info = owned_inspect(engine, container, name, labels)
        execution.setdefault('containerId', container)
        if info['State']['Running']:
            engine.command(['stop', '--time=1', container], check=False, timeout=8)
        engine.command(['rm', '--force', container], timeout=12)
        engine.owned.remove(container)
    cleanup['containerRemoved'] = not listing(engine)
    if 'processesBefore' in execution:
        cleanup['processesNotLive'] = original_processes_gone(execution['processesBefore'])
    if 'containerCgroup' in execution:
        cleanup['cgroupEmpty'] = group_empty(Path(execution['containerCgroup'])) and group_empty(engine.container_parent)


def safe_error(stage, error):
    if isinstance(error, (WorkerError, Blocked)):
        code = str(error)
    elif isinstance(error, subprocess.TimeoutExpired):
        code = 'E_TIMEOUT'
    elif isinstance(error, subprocess.CalledProcessError):
        code = 'E_SYSTEM_COMMAND'
    elif isinstance(error, RuntimeError) and str(error).startswith('E_PODMAN_COMMAND:'):
        code = 'E_PODMAN_COMMAND'
    else:
        code = 'E_WORKER_OPERATION'
    return {'stage': stage, 'code': code, 'type': type(error).__name__}


def run_worker(path, run_id, job_id):
    execution = {}
    cleanup = {'containerRemoved': None, 'processesNotLive': None, 'cgroupEmpty': None}
    evidence = {'workerVersion': WORKER_VERSION, 'runId': run_id, 'jobId': job_id, 'status': 'unresolved',
                'execution': execution, 'cleanup': cleanup, 'startedAt': datetime.now(timezone.utc).isoformat()}
    engine = None
    attempted = False
    name = 'qa-vf1-' + uuid.uuid4().hex
    labels = {'qa.vf1.owner': 'private-synthetic-v1', 'qa.vf1.run': run_id, 'qa.vf1.job': job_id}
    stage = 'validate-input'
    try:
        payloads, evidence['inputHashes'] = read_staging(path, run_id, job_id)
        stage = 'delegation'
        own_delegation()
        stage = 'private-engine'
        engine = VF1Engine.__new__(VF1Engine)
        engine.__init__()
        evidence['engine'] = {'rootless': engine.info['host']['security']['rootless'],
                              'podmanVersion': engine.info['version']['Version'], 'delegatedParent': str(engine.parent)}
        stage = 'image'
        evidence['image'] = engine.build_image()
        stage = 'stage-private-input'
        stage_private(engine, payloads)
        output_fd = os.open(engine.base / 'output', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            stage = 'launch'
            execution.update({'containerName': name, 'labels': labels, 'command': CONTAINER_COMMAND})
            attempted = True
            container = engine.launch_fixed(name, labels)
            execution['containerId'] = container
            stage = 'observe-live-scope'
            observe_live(engine, container, name, labels, execution)
            marker_fd = os.open('.allow-start', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC,
                                mode=0o400, dir_fd=output_fd)
            os.close(marker_fd)
            stage = 'wait-exit'
            outcome = engine.command(['wait', container], timeout=TIMEOUT_SECONDS + 4).stdout.strip()
            require(re.fullmatch(r'\d{1,3}', outcome), 'E_WAIT_STATUS')
            state = owned_inspect(engine, container, name, labels)['State']
            execution['exitCode'] = int(outcome)
            require(not state['Running'] and state['Pid'] == 0 and state['ExitCode'] == execution['exitCode'], 'E_EXIT_STATE')
            execution['containerStoppedPidZero'] = True
            require(execution['exitCode'] == 0, 'E_WRAPPER_EXIT')
            stage = 'collect-result'
            execution.update(collect_result(output_fd, run_id, job_id))
        finally:
            os.close(output_fd)
    except Exception as error:
        evidence['error'] = safe_error(stage, error)
    finally:
        if engine is not None and hasattr(engine, 'base'):
            evidence['privateCache'] = str(engine.base)
        if attempted:
            try:
                cleanup_job(engine, name, labels, execution, cleanup)
            except Exception as error:
                evidence['cleanupError'] = safe_error('cleanup', error)
    if 'error' not in evidence and 'cleanupError' not in evidence and all(value is True for value in cleanup.values()):
        evidence['status'] = 'complete'
    evidence['finishedAt'] = datetime.now(timezone.utc).isoformat()
    return evidence


def main():
    if len(sys.argv) != 4 or not all(IDENTIFIER.fullmatch(value) for value in sys.argv[2:]):
        print(json.dumps({'workerVersion': WORKER_VERSION, 'status': 'unresolved', 'error': {'code': 'E_WORKER_ARGS'}}))
        return 2
    evidence = run_worker(*sys.argv[1:])
    print(json.dumps(evidence, ensure_ascii=True, allow_nan=False, separators=(',', ':')), flush=True)
    return 0 if evidence['status'] == 'complete' else 2


if __name__ == '__main__':
    raise SystemExit(main())
