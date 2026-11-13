"""Trusted local supervisor and replaceable pipe child for the S4-E fixture."""
from pathlib import Path
import json
import os
import re
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'spikes/s4b'))
from engine import RootlessEngine
from run_engine import pid_state


def require(condition, code):
    if not condition:
        raise RuntimeError(code)


def child():
    for line in sys.stdin:
        request = json.loads(line)
        print(json.dumps(request), flush=True)
        result = json.loads(sys.stdin.readline())
        if request['op'] == 'crash' or (request['op'] == 'launch' and request.get('crash_after_launch') and result.get('ok')):
            os._exit(73)
        print(json.dumps(result), flush=True)


class Supervisor:
    def __init__(self):
        self.engine = RootlessEngine()
        self.generation = uuid.uuid4().hex
        self.boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        self.journal = self.engine.base / 's4e-journal.json'
        self.state = {'marker': 'qa-s4e-journal-v1', 'generation': self.generation, 'boot': self.boot, 'jobs': {}}
        self.save()
        self.image = self.engine.build_image()
        self.child = None
        self.pending_cleanup = None
        self.witness_available = True

    def save(self):
        temp = self.journal.with_suffix('.tmp')
        with temp.open('w') as f:
            json.dump(self.state, f, sort_keys=True); f.flush(); os.fsync(f.fileno())
        os.replace(temp, self.journal)
        fd = os.open(self.journal.parent, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(fd)
        finally: os.close(fd)

    def load(self):
        state = json.loads(self.journal.read_text())
        require(state == self.state and state['marker'] == 'qa-s4e-journal-v1', 'E_JOURNAL')
        require(Path('/proc/sys/kernel/random/boot_id').read_text().strip() == self.boot, 'E_BOOT')

    def binding(self, binding):
        require(type(binding) is dict and set(binding) == {'job', 'project', 'run_id', 'assignment_id', 'attempt', 'fence', 'generation', 'container_name'}, 'E_BINDING')
        require(type(binding['job']) is str and re.fullmatch('[a-f0-9]{32}', binding['job']), 'E_JOB')
        require(binding['generation'] == self.generation and binding['container_name'] == 'qa-s4e-' + binding['job'], 'E_BINDING')
        require(all(type(binding[k]) is str and binding[k] for k in ('project', 'run_id', 'assignment_id')), 'E_BINDING')
        require(all(type(binding[k]) is int and binding[k] > 0 for k in ('attempt', 'fence')), 'E_BINDING')
        return binding['job']

    def listing(self):
        listing = json.loads(self.engine.command(['ps', '--all', '--no-trunc', '--format=json']).stdout)
        require(type(listing) is list, 'E_LIST')
        return listing

    def observe(self, item):
        binding = item['binding']; rows = self.listing(); resource = item.get('resource')
        # The engine is private to this supervisor, so any unjournaled container is ambiguous.
        known = {j['resource']['containerId'] for j in self.state['jobs'].values() if j.get('resource') and not j.get('cleaned')}
        ids = [row.get('Id', row.get('ID')) for row in rows]
        require(all(isinstance(i, str) and re.fullmatch('[a-f0-9]{64}', i) for i in ids), 'E_LIST_ID')
        require(len(ids) == len(set(ids)) and set(ids) <= known, 'E_UNKNOWN_RESOURCE')
        require(resource is not None, 'E_NO_RESOURCE')
        cid = resource['containerId']
        if cid in ids:
            info = self.engine.inspect(cid)
            labels = info['Config']['Labels']
            expected = {'qa.s4.owner': 'private-fixture', 'qa.s4e.job': binding['job'], 'qa.s4e.generation': binding['generation'],
                        'qa.s4e.fence': str(binding['fence']), 'qa.s4e.assignment': binding['assignment_id'], 'qa.s4e.attempt': str(binding['attempt'])}
            require(info['Id'] == cid and info['Name'].lstrip('/') == binding['container_name'] and all(labels.get(k) == v for k, v in expected.items()), 'E_RESOURCE_BINDING')
            running = info['State']['Running']
            if running:
                require(str(info['State']['Pid']) in resource['processes'], 'E_PROCESS_IDENTITY')
                require(str(self.engine.cgroup(cid)) == resource['cgroup'], 'E_CGROUP')
                for pid, original in resource['processes'].items():
                    now = pid_state(int(pid))
                    require(now is None or now['startTime'] == original['startTime'], 'E_PROCESS_IDENTITY')
            return {'containerId': cid, 'present': True, 'running': running, 'resource': resource}
        return {'containerId': cid, 'present': False, 'running': False, 'resource': resource}

    def launch(self, item):
        b = item['binding']; e = self.engine
        labels = {'qa.s4.owner': 'private-fixture', 'qa.s4e.job': b['job'], 'qa.s4e.generation': b['generation'], 'qa.s4e.fence': str(b['fence']), 'qa.s4e.assignment': b['assignment_id'], 'qa.s4e.attempt': str(b['attempt'])}
        args = ['run', '-d', '--pull=never', '--name', b['container_name']]
        for key, value in labels.items(): args += ['--label', key + '=' + value]
        args += ['--userns=keep-id', '--user=1000:1000', '--read-only', '--read-only-tmpfs=false', '--cap-drop=all', '--security-opt=no-new-privileges', '--network=none', '--memory', '64m', '--memory-swap', '64m', '--pids-limit', '32', '--cpus', '0.5', '--cgroup-parent', str(e.container_parent).removeprefix('/sys/fs/cgroup'), '--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=8m,mode=1777', '--volume', str(e.base / 'input') + ':/input:ro', '--volume', str(e.base / 'output') + ':/output:rw', e.image, '/bin/sh', '-c', 'sleep 180 & sleep 180 & wait']
        cid = e.command(args).stdout.strip()
        require(re.fullmatch('[a-f0-9]{64}', cid), 'E_CONTAINER_ID')
        e.owned.append(cid)
        group = e.cgroup(cid)
        deadline = time.monotonic() + 3
        while True:
            pids = (group / 'cgroup.procs').read_text().split()
            if len(pids) >= 3 or time.monotonic() >= deadline: break
            time.sleep(.01)
        processes = {p: pid_state(int(p)) for p in pids}
        require(len(processes) >= 3 and all(processes.values()), 'E_PROCESS')
        item['resource'] = {'containerId': cid, 'cgroup': str(group), 'processes': processes, 'bootId': self.boot}
        self.save()
        return self.observe(item)

    def execute(self, req):
        op = req.get('op')
        if op == 'witness_access':
            require(type(req.get('available')) is bool, 'E_FAULT_ARGUMENT')
            self.witness_available = req['available']
            return {'available': self.witness_available}
        require(self.witness_available, 'E_WITNESS_UNAVAILABLE')
        self.load()
        if op == 'crash': return {'crashed': True}
        b = req.get('binding'); job = self.binding(b)
        if op == 'register':
            require(job not in self.state['jobs'], 'E_DUPLICATE')
            self.state['jobs'][job] = {'binding': b, 'attempted': False, 'epoch': 0, 'cleaned': False}
            self.save(); return {'registered': True}
        item = self.state['jobs'].get(job)
        require(item is not None and item['binding'] == b, 'E_BINDING')
        if op == 'launch':
            require(not item['attempted'] and not item['cleaned'] and item['epoch'] == 0, 'E_LAUNCH_REPLAY')
            item['attempted'] = True; self.save()
            return self.launch(item)
        if op == 'discover':
            observation = self.observe(item)
            if 'expected_resource' in req: require(req['expected_resource'] == item['resource'], 'E_RESOURCE_BINDING')
            return observation
        if op == 'pause_cleanup':
            require(self.pending_cleanup is None and type(req.get('epoch')) is int and req['epoch'] == item['epoch'] and item['epoch'] > 0, 'E_EPOCH')
            require(req.get('expected_resource') == item.get('resource') and item.get('resource') is not None, 'E_RESOURCE_BINDING')
            self.pending_cleanup = {'op': 'cleanup', 'binding': b, 'epoch': req['epoch'], 'expected_resource': req['expected_resource']}
            return {'paused': True, 'epoch': req['epoch']}
        if op == 'resume_cleanup':
            require(self.pending_cleanup is not None and self.pending_cleanup['binding'] == b, 'E_NO_PENDING')
            pending = self.pending_cleanup; self.pending_cleanup = None
            return self.execute(pending)
        if op == 'fence':
            epoch = req.get('epoch')
            require(type(epoch) is int and epoch > item['epoch'] and not item['cleaned'], 'E_EPOCH')
            item['epoch'] = epoch; self.save(); return {'epoch': epoch}
        if op == 'cleanup':
            epoch = req.get('epoch')
            require(type(epoch) is int and epoch > 0 and epoch == item['epoch'] and not item['cleaned'], 'E_EPOCH')
            require(req.get('expected_resource') == item.get('resource') and item.get('resource') is not None, 'E_RESOURCE_BINDING')
            observation = self.observe(item)
            require(observation['present'], 'E_RESOURCE_ABSENT')
            resource = item['resource']; cid = resource['containerId']
            self.engine.command(['stop', '--time=1', cid], timeout=12)
            stopped = self.engine.inspect(cid)['State']
            require(not stopped['Running'] and stopped['Pid'] == 0, 'E_STOP')
            for pid, original in resource['processes'].items():
                now = pid_state(int(pid))
                require(now is None or now['state'] == 'Z' or now['startTime'] != original['startTime'], 'E_PROCESS_LIVE')
            group = Path(resource['cgroup'])
            require(not group.exists() or not (group / 'cgroup.procs').read_text().strip(), 'E_CGROUP_LIVE')
            self.engine.command(['rm', cid])
            require(cid not in [row.get('Id', row.get('ID')) for row in self.listing()], 'E_REMOVE')
            self.engine.owned.remove(cid); item['cleaned'] = True; self.save()
            return {'epoch': epoch, 'binding': b, 'containerId': cid, 'resource': resource, 'originalProcessesNotLive': True, 'cgroupEmptyOrRemoved': True, 'containerRemoved': True}
        raise RuntimeError('E_OP')

    # One supervisor request loop serializes witness advancement and all engine IO.
    # pause/resume is a trusted test hook: resume re-enters the same epoch check.
    def relay(self, req):
        if self.child is None or self.child.poll() is not None:
            self.child = subprocess.Popen([sys.executable, '-B', __file__, '--child'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        c = self.child
        c.stdin.write(json.dumps(req) + '\n'); c.stdin.flush()
        require(json.loads(c.stdout.readline()) == req, 'E_CHILD')
        try: reply = {'ok': True, 'result': self.execute(req)}
        except Exception as exc: reply = {'ok': False, 'code': str(exc)}
        c.stdin.write(json.dumps(reply) + '\n'); c.stdin.flush()
        line = c.stdout.readline()
        if not line:
            status = c.wait(timeout=5)
            require(status == 73, 'E_CHILD_EXIT')
            return {'ok': True, 'result': {'crashed': True, 'exitCode': status, 'childPid': c.pid, 'supervisorPid': os.getpid()}}
        reply = json.loads(line)
        if reply.get('ok'): reply['result']['childPid'] = c.pid
        return reply


def main():
    supervisor = Supervisor(); e = supervisor.engine
    print(json.dumps({'ready': True, 'generation': supervisor.generation, 'hostUid': 1000, 'image': supervisor.image, 'delegatedParent': str(e.parent), 'privateCache': str(e.base), 'supervisorPid': os.getpid(), 'helperRole': 'replaceable pipe child; supervisor owns engine'}), flush=True)
    try:
        for line in sys.stdin:
            try: print(json.dumps(supervisor.relay(json.loads(line))), flush=True)
            except Exception as exc: print(json.dumps({'ok': False, 'code': str(exc)}), flush=True)
    finally:
        if supervisor.child and supervisor.child.poll() is None:
            supervisor.child.stdin.close(); supervisor.child.wait(timeout=5)
        # The caller must reconcile first; do not silently remove unresolved containers.
        require(not e.owned and not supervisor.listing(), 'E_UNRESOLVED_CLOSE')
        observation = e.cleanup()
        print(json.dumps({'closed': True, 'cleanup': observation}), flush=True)


if __name__ == '__main__':
    child() if sys.argv[1:] == ['--child'] else main()
