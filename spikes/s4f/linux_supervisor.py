"""Trusted private S4-F Linux process. Replacement and observer never initialize an engine."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'spikes/s4b'))
from engine import RootlessEngine
from run_engine import pid_state

COMMAND = ['/bin/sh', '-c', 'sleep 180 & sleep 180 & wait']
GROUPS = Path('/sys/fs/cgroup/system.slice')
DIRS = ('home', 'runtime', 'storage', 'runroot', 'config', 'data', 'cache', 'input', 'output')
UNIT = re.compile(r'qa-s4-f-[a-f0-9]{16}\.service')


def check(condition, code):
    if not condition:
        raise RuntimeError(code)


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def boot():
    return Path('/proc/sys/kernel/random/boot_id').read_text().strip()


def process(pid):
    state = pid_state(pid)
    return {'pid': pid, 'startTime': state['startTime']} if state and state['state'] != 'Z' else None


def fsid(path, directory):
    info = path.lstat()
    check((stat.S_ISDIR if directory else stat.S_ISREG)(info.st_mode) and info.st_uid == os.getuid(),
          'E_CONTEXT_OBJECT')
    return [info.st_dev, info.st_ino]


def atomic(path, value):
    tmp = path.with_name('.s4f-' + uuid.uuid4().hex)
    with tmp.open('xb') as stream:
        stream.write(encoded(value))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)
    fd = os.open(path.parent, os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def load(path):
    fsid(path, False)
    with path.open('rb') as stream:
        raw = stream.read(128 * 1024 + 1)
    check(len(raw) <= 128 * 1024, 'E_DOCUMENT')
    try:
        return json.loads(raw)
    except ValueError:
        raise RuntimeError('E_DOCUMENT') from None


def unit_state(unit):
    check(UNIT.fullmatch(unit), 'E_UNIT')
    out = subprocess.run(['systemctl', 'show', unit, '--property=LoadState,ActiveState,MainPID,InvocationID'],
                         capture_output=True, text=True, timeout=5)
    props = dict(line.split('=', 1) for line in out.stdout.splitlines() if '=' in line)
    check(props.get('LoadState') in ('loaded', 'not-found') and props.get('ActiveState')
          and (out.returncode == 0 or props['LoadState'] == 'not-found'), 'E_UNIT_STATE')
    return props


def original_absent(ctx):
    unit = ctx['unit']
    props = unit_state(unit)
    check(props['LoadState'] == 'not-found' and props['ActiveState'] == 'inactive'
          and not (GROUPS / unit).exists() and process(ctx['supervisor']['pid']) != ctx['supervisor'], 'E_OLD_WRITER')
    return {'unit': unit, 'loadState': props['LoadState'], 'activeState': props['ActiveState'],
            'originalCgroupAbsent': True, 'originalProcessNotLive': True}


def landmarks(base):
    paths = {name: fsid(base / name, True) for name in DIRS}
    for name in ('marker.json', 'containers.conf', 'auth.json', 's4f.lock'):
        paths[name] = [fsid(base / name, False), hashlib.sha256((base / name).read_bytes()).hexdigest()]
    return paths


def pause_identity(engine):
    path = engine.base / 'runtime/libpod/tmp/pause.pid'
    identity = fsid(path, False)
    raw = path.read_bytes()
    check(len(raw) < 32 and re.fullmatch(rb'[1-9][0-9]*\n?', raw), 'E_PAUSE_IDENTITY')
    pid = int(raw)
    live = process(pid)
    check(live, 'E_PAUSE_IDENTITY')
    proc = Path('/proc') / str(pid)
    return {'fileId': identity, 'parentId': fsid(path.parent, True), 'rawSha256': hashlib.sha256(raw).hexdigest(),
            'process': live, 'uidMap': (proc / 'uid_map').read_text(), 'gidMap': (proc / 'gid_map').read_text()}


def file_anchor(path):
    return {'fileId': fsid(path, False), 'parentId': fsid(path.parent, True),
            'rawSha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def context(engine, unit):
    props = unit_state(unit)
    check((engine.parent, int(props['MainPID'])) == (GROUPS / unit, os.getpid()) and props['InvocationID'],
          'E_WRITER_ID')
    (engine.base / 's4f.lock').touch(exist_ok=False)
    unit_process = process(os.getpid())
    check(unit_process, 'E_WRITER_ID')
    return {'version': 's4f-context-v3', 'generation': uuid.uuid4().hex, 'uid': os.getuid(), 'boot': boot(),
            'base': str(engine.base), 'baseId': fsid(engine.base, True), 'landmarks': landmarks(engine.base),
            'unit': unit, 'invocation': props['InvocationID'], 'supervisor': unit_process, 'image': engine.image,
            'pause': pause_identity(engine), 'alive': file_anchor(engine.base / 'runtime/libpod/tmp/alive'),
            'aliveLock': fsid(engine.base / 'runtime/libpod/tmp/alive.lck', False)}


def attach(ctx):
    base = Path(ctx['base'])
    check(base.parent == Path('/tmp') and re.fullmatch(r'qa-s4-engine-[a-z0-9_]{8}', base.name)
          and UNIT.fullmatch(ctx['unit']) and os.getuid() == ctx['uid'] == 1000 and ctx['boot'] == boot(),
          'E_CONTEXT')
    check(ctx['version'] == 's4f-context-v3' and isinstance(ctx.get('pause'), dict), 'E_CONTEXT')
    check(ctx['baseId'] == fsid(base, True) and base.stat().st_mode & 0o077 == 0 and
          ctx['landmarks'] == landmarks(base) and load(base / 's4f-context.json') == ctx and
          load(base / 'marker.json') == {'kind': 'qa-s4-private-engine-v1', 'uid': 1000}, 'E_CONTEXT')
    # __init__ creates a new store. Attach only the exact inspected original file identities.
    engine = object.__new__(RootlessEngine)
    engine.base, engine.image = base, ctx['image']
    engine.container_parent = GROUPS / ctx['unit'] / 'containers'
    engine.env = {'PATH': '/usr/bin:/bin', 'HOME': str(base / 'home'), 'XDG_RUNTIME_DIR': str(base / 'runtime'),
                  'XDG_CONFIG_HOME': str(base / 'config'), 'XDG_DATA_HOME': str(base / 'data'),
                  'XDG_CACHE_HOME': str(base / 'cache'), 'REGISTRY_AUTH_FILE': str(base / 'auth.json'),
                  'CONTAINERS_CONF': str(base / 'containers.conf'), 'LANG': 'C.UTF-8'}
    engine.prefix = ['/usr/bin/podman', '--root', str(base / 'storage'), '--runroot', str(base / 'runroot'),
                     '--storage-driver=vfs', '--cgroup-manager=cgroupfs', '--events-backend=file', '--runtime=/usr/bin/crun']
    return engine


def engine_identity(engine):
    info = json.loads(engine.command(['info', '--format=json']).stdout)
    store = info['store']
    check(info['host']['security']['rootless'] is True and store['graphDriverName'] == 'vfs' and
          Path(store['graphRoot']) == engine.base / 'storage' and Path(store['runRoot']) == engine.base / 'runroot',
          'E_ENGINE_ID')
    image = json.loads(engine.command(['image', 'inspect', engine.image]).stdout)
    check(len(image) == 1 and image[0]['Id'].removeprefix('sha256:') == engine.image.removeprefix('sha256:'),
          'E_IMAGE_ID')


def labeled(binding):
    return {'qa.s4f.' + key: str(binding[key]) for key in
            ('job', 'effectNonce', 'project', 'run_id', 'assignment_id', 'attempt', 'fence', 'generation')}


def binding_ok(binding, ctx):
    required = {'job', 'effectNonce', 'project', 'run_id', 'assignment_id', 'attempt', 'fence', 'generation', 'container_name'}
    check(type(binding) is dict and set(binding) == required and binding['generation'] == ctx['generation']
          and all(re.fullmatch(r'[0-9a-f]{32}', binding[k]) for k in ('job', 'effectNonce'))
          and binding['container_name'] == 'qa-s4-f-' + binding['job']
          and all(isinstance(binding[k], str) and re.fullmatch(r'[A-Za-z0-9_-]{1,96}', binding[k])
                  for k in ('project', 'run_id', 'assignment_id'))
          and all(type(binding[k]) is int and binding[k] > 0 for k in ('attempt', 'fence')), 'E_BINDING')


def listing(engine, broken=False):
    args = ['ps', '--all', '--no-trunc', '--format=json']
    if broken is True:
        args.append('--s4f-deliberately-invalid-option')
    reply = engine.command(args, check=False)
    check(reply.returncode == 0, 'E_LISTING')
    try:
        rows = json.loads(reply.stdout[:len(reply.stdout) // 2] if broken == 'truncated' else reply.stdout)
    except ValueError:
        raise RuntimeError('E_LISTING') from None
    check(isinstance(rows, list), 'E_LISTING')
    ids = [r.get('Id', r.get('ID')) for r in rows]
    check(all(isinstance(cid, str) and re.fullmatch('[0-9a-f]{64}', cid) for cid in ids)
          and len(set(ids)) == len(ids), 'E_LISTING')
    return ids


def create(engine, binding):
    check(not listing(engine), 'E_UNKNOWN_RESOURCE')
    args = ['create', '--pull=never', '--name', binding['container_name']]
    for key, value in labeled(binding).items():
        args.extend(['--label', key + '=' + value])
    args.extend(['--userns=keep-id', '--user=1000:1000', '--read-only', '--read-only-tmpfs=false',
                 '--cap-drop=all', '--security-opt=no-new-privileges', '--network=none', '--memory=64m',
                 '--memory-swap=64m', '--pids-limit=32', '--cpus=0.5',
                 '--cgroup-parent', str(engine.container_parent).removeprefix('/sys/fs/cgroup'),
                 '--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=8m,mode=1777',
                 '--volume', str(engine.base / 'input') + ':/input:ro',
                 '--volume', str(engine.base / 'output') + ':/output:rw', engine.image, *COMMAND])
    cid = engine.command(args).stdout.strip()
    check(re.fullmatch('[a-f0-9]{64}', cid), 'E_CONTAINER_ID')
    return cid


def inspect_resource(engine, ctx, binding, cid):
    row, = json.loads(engine.command(['inspect', '--type=container', cid]).stdout)
    cfg, host, state = row['Config'], row['HostConfig'], row['State']
    check(row['Id'] == cid and row['Name'].lstrip('/') == binding['container_name'] and
          row['Image'].removeprefix('sha256:') == ctx['image'].removeprefix('sha256:') and
          all(cfg['Labels'].get(k) == v for k, v in labeled(binding).items()) and
          cfg['Cmd'] == COMMAND and cfg['User'] == '1000:1000' and host['ReadonlyRootfs'] is True and
          host['NetworkMode'] == 'none' and host['CgroupParent'] == str(engine.container_parent).removeprefix('/sys/fs/cgroup'),
          'E_CONTAINER_CONFIG')
    mounts = {m['Destination']: (m['Source'], m['RW']) for m in row['Mounts'] if m.get('Type') == 'bind'}
    check(mounts == {'/input': (str(engine.base / 'input'), False), '/output': (str(engine.base / 'output'), True)},
          'E_MOUNTS')
    result = {'containerId': cid, 'status': state['Status'], 'running': state['Running'],
              'initPid': state['Pid'], 'boot': ctx['boot'], 'processes': {}, 'cgroup': None}
    if result['running']:
        check(result['initPid'] > 0, 'E_PROCESS')
        path = Path('/proc') / str(result['initPid']) / 'cgroup'
        group = Path('/sys/fs/cgroup') / next(s[3:] for s in path.read_text().splitlines() if s.startswith('0::')).lstrip('/')
        check(engine.container_parent in group.parents, 'E_CGROUP')
        deadline = time.monotonic() + 3
        while True:
            pids = (group / 'cgroup.procs').read_text().split()
            if len(pids) >= 3 or time.monotonic() >= deadline:
                break
            time.sleep(.025)
        identities = {pid: process(int(pid)) for pid in pids}
        check(str(result['initPid']) in identities and len(identities) >= 3 and all(identities.values()), 'E_PROCESS')
        result.update(cgroup=str(group), processes=identities)
    else:
        check(result['initPid'] == 0 and result['status'] in ('configured', 'created', 'stopped', 'exited'),
              'E_NOT_STOPPED')
    return result


def old_processes_gone(resource, engine):
    for pid, original in resource['processes'].items():
        check(process(int(pid)) != original, 'E_PROCESS_LIVE')
    if resource['cgroup'] is not None:
        group = Path(resource['cgroup'])
        check(engine.container_parent in group.parents and (not group.exists() or
              not (group / 'cgroup.procs').read_text().strip()), 'E_CGROUP_LIVE')


class Supervisor:
    def __init__(self, ctx, engine, role):
        self.ctx, self.engine, self.role = ctx, engine, role
        self.journal = engine.base / 's4f-journal.json'
        self.fired = False
        self.pause_repair = None
        self.engine_checked = False
        self.lock = None
        if role != 'observer':
            self.lock = (engine.base / 's4f.lock').open('rb')
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if role != 'replacement':
            engine_identity(engine)
            self.engine_checked = True

    def ensure_engine(self, state):
        if self.engine_checked:
            return
        quiet = original_absent(self.ctx)
        old = self.ctx['pause']
        check(process(old['process']['pid']) != old['process'], 'E_PAUSE_LIVE')
        path = self.engine.base / 'runtime/libpod/tmp/pause.pid'
        check(fsid(path.parent, True) == old['parentId'] and fsid(path, False) == old['fileId']
              and hashlib.sha256(path.read_bytes()).hexdigest() == old['rawSha256'], 'E_PAUSE_IDENTITY')
        check(file_anchor(path.with_name('alive')) == self.ctx['alive'], 'E_PAUSE_IDENTITY')
        check(state['epoch'] > 0 and state['contextPin'] == digest(self.ctx), 'E_FENCE')
        receipt_path = self.engine.base / 's4f-pause-repair.json'
        check(not receipt_path.exists(), 'E_PAUSE_UNCERTAIN')
        receipt = {'version': 's4f-pause-repair-v1', 'contextPin': digest(self.ctx), 'binding': state['binding'],
                   'epoch': state['epoch'], 'journalPin': digest(state), 'oldPause': old,
                   'oldAlive': self.ctx['alive'], 'quiescence': quiet, 'phase': 'intent'}
        parent = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            check([os.fstat(parent).st_dev, os.fstat(parent).st_ino] == old['parentId'], 'E_PAUSE_IDENTITY')
            lock = os.open('alive.lck', os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent)
            try:
                li = os.fstat(lock)
                check(stat.S_ISREG(li.st_mode) and li.st_uid == 1000 and [li.st_dev, li.st_ino] == self.ctx['aliveLock'], 'E_PAUSE_IDENTITY')
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                atomic(receipt_path, receipt)
                for name, anchor in [('pause.pid', old), ('alive', self.ctx['alive'])]:
                    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent)
                    try:
                        info = os.fstat(fd)
                        check(stat.S_ISREG(info.st_mode) and info.st_uid == 1000 and [info.st_dev, info.st_ino] == anchor['fileId']
                              and hashlib.sha256(os.read(fd, 4096)).hexdigest() == anchor['rawSha256']
                              and process(old['process']['pid']) != old['process'], 'E_PAUSE_IDENTITY')
                        os.unlink(name, dir_fd=parent)
                    finally:
                        os.close(fd)
                os.fsync(parent)
            finally:
                os.close(lock)
        finally:
            os.close(parent)
        engine_identity(self.engine)
        new = pause_identity(self.engine)
        check(new['uidMap'] == old['uidMap'] and new['gidMap'] == old['gidMap'], 'E_NAMESPACE_MAP')
        receipt.update(phase='helper_recreated', newPause=new)
        atomic(receipt_path, receipt)
        self.pause_repair, self.engine_checked = receipt, True

    def state(self, req):
        try:
            state = load(self.journal)
        except FileNotFoundError:
            raise RuntimeError('E_JOURNAL') from None
        check(digest(state) == req['journalPin'] and state['contextPin'] == digest(self.ctx), 'E_JOURNAL')
        check(state['binding'] == req['binding'], 'E_BINDING')
        return state

    def save(self, state):
        if self.journal.exists():
            atomic(self.engine.base / 's4f-previous.json', load(self.journal))
        atomic(self.journal, state)
        return digest(state)

    def inspect(self, state, broken=False):
        self.ensure_engine(state)
        ids = listing(self.engine, broken)
        check(len(ids) <= 1, 'E_UNKNOWN_RESOURCE')
        saved = state.get('resource')
        if not ids:
            if saved:
                old_processes_gone(saved, self.engine)
            return None
        cid, = ids
        check(saved is None or cid == saved['containerId'], 'E_IDENTITY')
        actual = inspect_resource(self.engine, self.ctx, state['binding'], cid)
        if saved:
            if actual['running']:
                check(saved == actual, 'E_IDENTITY')
            else:
                old_processes_gone(saved, self.engine)
        return actual

    def execute(self, req):
        op, b = req['op'], req['binding']
        binding_ok(b, self.ctx)
        if op == 'arm':
            check(self.role == 'original' and not self.journal.exists(), 'E_ONE_USE')
            check(not listing(self.engine), 'E_UNKNOWN_RESOURCE')
            state = {'binding': b, 'contextPin': digest(self.ctx), 'epoch': 0, 'phase': 'consumed', 'resource': None}
            return {'journalPin': self.save(state)}
        state = self.state(req)
        if self.role == 'original':
            check(op == 'fire' and not self.fired and state['phase'] == 'consumed' and
                  req['window'] in ('before_create', 'after_create', 'after_start', 'after_identity'), 'E_ONE_USE')
            self.fired = True
            if req['window'] == 'before_create':
                return {'barrier': req['window'], 'journalPin': digest(state)}
            cid = create(self.engine, b)
            if req['window'] != 'after_create':
                self.engine.command(['start', cid])
            if req['window'] == 'after_identity':
                state['resource'] = self.inspect(state)
                state['phase'] = 'identified'
                self.save(state)
            return {'barrier': req['window'], 'journalPin': digest(state), 'resource': state['resource']}
        if self.role == 'observer':
            check(op == 'observe', 'E_ROLE')
            return {'resource': self.inspect(state), 'observer': process(os.getpid())}
        quiet = original_absent(self.ctx)
        check(state['phase'] in ('consumed', 'identified'), 'E_NO_REPLAY')
        if op == 'fence':
            check(req['epoch'] == state['epoch'] + 1, 'E_FENCE')
            state['epoch'] = req['epoch']
            return {'journalPin': self.save(state)}
        check(req['epoch'] == state['epoch'] and state['epoch'] > 0, 'E_FENCE')
        if 'expectedResource' in req:
            check(req['expectedResource'] == state['resource'], 'E_IDENTITY')
        if op == 'test_journal':
            fault = req['fault']
            check(fault in ('absent', 'corrupt', 'older'), 'E_ROLE')
            try:
                if fault == 'absent':
                    self.journal.unlink()
                elif fault == 'corrupt':
                    atomic(self.journal, {'corruptTest': True})
                else:
                    atomic(self.journal, load(self.engine.base / 's4f-previous.json'))
                try:
                    self.state(req)
                except RuntimeError as exc:
                    check(str(exc) == 'E_JOURNAL', 'E_WRONG_DENIAL')
                    return {'fault': fault, 'denied': 'E_JOURNAL'}
                raise RuntimeError('E_FAULT_ACCEPTED')
            finally:
                # Same exclusive fixture lock, exact previously authenticated file.
                atomic(self.journal, state)
        if op == 'test_runtime_anchor':
            check(not self.engine_checked and req['fault'] in ('missing_pause', 'substituted_pause', 'changed_alive'), 'E_ROLE')
            path = self.engine.base / 'runtime/libpod/tmp' / ('alive' if req['fault'] == 'changed_alive' else 'pause.pid')
            original = path.read_bytes()
            held = path.with_name('.s4f-held-' + uuid.uuid4().hex)
            repair = self.engine.base / 's4f-pause-repair.json'
            check(not repair.exists(), 'E_PAUSE_UNCERTAIN')
            changed_in_place = req['fault'] == 'changed_alive'
            try:
                if changed_in_place:
                    path.write_bytes(original + b'changed')
                else:
                    os.rename(path, held)
                    if req['fault'] == 'substituted_pause':
                        path.write_bytes(original)
                try:
                    self.ensure_engine(state)
                except (RuntimeError, FileNotFoundError) as exc:
                    check(isinstance(exc, FileNotFoundError) or str(exc) == 'E_PAUSE_IDENTITY', 'E_WRONG_DENIAL')
                    check(not repair.exists(), 'E_PREMATURE_REPAIR')
                    return {'fault': req['fault'], 'denied': 'E_PAUSE_IDENTITY', 'repairIntentWritten': False}
                raise RuntimeError('E_FAULT_ACCEPTED')
            finally:
                if changed_in_place:
                    path.write_bytes(original)
                else:
                    if path.exists():
                        path.unlink()
                    os.rename(held, path)
                check(file_anchor(path) == (self.ctx['alive'] if changed_in_place else
                      {key: self.ctx['pause'][key] for key in ('fileId', 'parentId', 'rawSha256')}), 'E_PAUSE_IDENTITY')
        if op == 'test_unknown_container':
            self.ensure_engine(state)
            before = listing(self.engine)
            check(len(before) == 1, 'E_TEST_SETUP')
            name = 's4f-injected-unknown-' + uuid.uuid4().hex
            cid = self.engine.command(['create', '--pull=never', '--name', name, '--network=none', '--read-only',
                                       self.engine.image, '/bin/true']).stdout.strip()
            check(re.fullmatch('[a-f0-9]{64}', cid) and cid not in before, 'E_CONTAINER_ID')
            try:
                try:
                    self.inspect(state)
                except RuntimeError as exc:
                    check(str(exc) == 'E_UNKNOWN_RESOURCE' and set(listing(self.engine)) == set(before + [cid]), 'E_WRONG_DENIAL')
                else:
                    raise RuntimeError('E_FAULT_ACCEPTED')
            finally:
                row, = json.loads(self.engine.command(['inspect', '--type=container', cid]).stdout)
                check(row['Id'] == cid and row['Name'].lstrip('/') == name and not row['State']['Running']
                      and row['State']['Pid'] == 0 and row['Image'].removeprefix('sha256:') == self.engine.image.removeprefix('sha256:'),
                      'E_TEST_RESOURCE_IDENTITY')
                self.engine.command(['rm', cid])  # only the independently created inactive test fault
            check(listing(self.engine) == before, 'E_TEST_RESOURCE_REMAINS')
            return {'denied': 'E_UNKNOWN_RESOURCE', 'originalContainerUntouched': True, 'injectedInactiveContainerRemoved': True}
        broken = 'truncated' if op == 'truncated_listing' else op == 'failed_listing'
        actual = self.inspect(state, broken=broken)
        if op == 'discover':
            return {'resource': actual, 'quiescence': quiet}
        check(op in ('cleanup', 'safety_teardown'), 'E_ROLE')
        if actual:
            cid = actual['containerId']
            if actual['running']:
                self.engine.command(['stop', '--time=1', cid])
            stopped = inspect_resource(self.engine, self.ctx, b, cid)
            check(not stopped['running'] and stopped['initPid'] == 0, 'E_NOT_STOPPED')
            old_processes_gone(actual, self.engine)
            self.engine.command(['rm', cid])
        check(not listing(self.engine) and not self.engine.container_parent.exists(), 'E_CLEANUP')
        if state['resource']:
            old_processes_gone(state['resource'], self.engine)
        proof = {'binding': b, 'epoch': state['epoch'], 'contextPin': digest(self.ctx), 'discovered': actual,
                 'durableOriginal': state['resource'], 'remainingContainerIds': [], 'quiescence': quiet,
                 'cgroupAbsent': not self.engine.container_parent.exists(), 'operation': op}
        proof['pauseRepair'] = self.pause_repair
        state.update(phase='safety_only' if op == 'safety_teardown' else 'cleaned', proof=proof)
        return {'journalPin': self.save(state), 'proof': proof}


def main():
    role, unit = sys.argv[1:]
    check(role in ('original', 'replacement', 'observer'), 'E_ROLE')
    if role == 'original':
        engine = RootlessEngine()
        image = engine.build_image()
        ctx = context(engine, unit)
        atomic(engine.base / 's4f-context.json', ctx)
    else:
        req = json.loads(sys.stdin.readline())
        ctx = req['context']
        check(digest(ctx) == req['contextPin'], 'E_CONTEXT')
        engine = attach(ctx)
        if role == 'replacement':
            original_absent(ctx)
        image = None
    supervisor = Supervisor(ctx, engine, role)
    print(json.dumps({'ready': True, 'context': ctx, 'contextPin': digest(ctx), 'image': image,
                      'process': process(os.getpid()), 'unit': unit}), flush=True)
    for line in sys.stdin:
        try:
            result = supervisor.execute(json.loads(line))
            reply = {'ok': True, 'result': result}
        except (ValueError, KeyError, OSError, RuntimeError, StopIteration) as exc:
            import traceback
            traceback.print_exc(file=sys.stderr)  # private owned-unit diagnostic, never ordinary application output
            code = str(exc).partition(':')[0]
            reply = {'ok': False, 'code': code if re.fullmatch('E_[A-Z_]+', code) else 'E_OBSERVATION'}
        print(json.dumps(reply), flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        code = str(exc).partition(':')[0]
        print(json.dumps({'ready': False, 'code': code if re.fullmatch('E_[A-Z_]+', code) else 'E_START'}), flush=True)
        raise
