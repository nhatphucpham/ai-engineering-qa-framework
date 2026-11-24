"""Windows operator pipe to one explicitly owned transient Linux unit."""
from pathlib import Path
import json
import queue
import subprocess
import threading
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
WSL = ['wsl.exe', '-d', 'Ubuntu-24.04', '-u', 'root', '--']
HIDDEN = getattr(subprocess, 'CREATE_NO_WINDOW', 0)


def check(ok, code):
    if not ok:
        raise RuntimeError(code)


def wsl(*args):
    return subprocess.run([*WSL, *args], capture_output=True, text=True, timeout=15, creationflags=HIDDEN)


class Unit:
    def __init__(self, role, workspace, anchor=None):
        self.name = 'qa-s4-f-' + uuid.uuid4().hex[:16] + '.service'
        translated = wsl('wslpath', '-a', (ROOT / 'spikes/s4f/linux_supervisor.py').as_posix())
        check(translated.returncode == 0 and translated.stdout.startswith('/'), 'E_WSLCONFIG')
        cmd = WSL + ['systemd-run', '--wait', '--pipe', '--collect', '--unit=' + self.name,
                     '--property=User=phucpn', '--property=Group=phucpn', '--property=Delegate=yes',
                     '--property=DelegateSubgroup=supervisor', '--property=KillMode=control-group',
                     '--property=MemoryMax=512M', '--property=TasksMax=256', '--property=RuntimeMaxSec=240',
                     '/usr/bin/python3', '-B', translated.stdout.strip(), role, self.name]
        self.log = (workspace / (self.name + '.stderr')).open('xb')
        self.output_log = (workspace / (self.name + '.stdout')).open('xb')
        self.process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.log,
                                        text=True, encoding='utf-8', creationflags=HIDDEN)
        self.lines = queue.Queue()
        self.closed = False
        self.thread = threading.Thread(target=self.read_output, daemon=True)
        self.thread.start()
        try:
            if anchor is not None:
                self.send(anchor)
            self.ready = self.receive()
            check(self.ready.get('ready'), self.ready.get('code', 'E_UNIT_START'))
            check(self.ready['unit'] == self.name, 'E_UNIT_START')
            if anchor is not None:
                check(self.ready['context'] == anchor['context'] and self.ready['contextPin'] == anchor['contextPin'],
                      'E_CONTEXT')
        except BaseException:
            self.close()
            raise

    def read_output(self):
        try:
            for line in self.process.stdout:
                self.output_log.write(line.encode('utf-8')); self.output_log.flush()
                self.lines.put(line)
        finally:
            self.lines.put(None)

    def send(self, value):
        try:
            self.process.stdin.write(json.dumps(value, separators=(',', ':')) + '\n')
            self.process.stdin.flush()
        except (OSError, ValueError):
            raise RuntimeError('E_CHANNEL') from None

    def receive(self):
        try:
            line = self.lines.get(timeout=45)
            check(line, 'E_CHANNEL')
            return json.loads(line)
        except (queue.Empty, ValueError):
            raise RuntimeError('E_CHANNEL') from None

    def request(self, op, **fields):
        self.send(dict(fields, op=op))
        reply = self.receive()
        if not reply.get('ok'):
            raise RuntimeError(reply.get('code', 'E_CHANNEL'))
        return reply['result']

    def absence(self):
        path = '/sys/fs/cgroup/system.slice/' + self.name
        limit = time.monotonic() + 8
        while time.monotonic() < limit:
            props = wsl('systemctl', 'show', self.name, '--property=LoadState,ActiveState')
            values = dict(v.split('=', 1) for v in props.stdout.splitlines() if '=' in v)
            if values.get('LoadState') == 'not-found' and values.get('ActiveState') == 'inactive':
                # Positive directory enumeration in parent plus test, not error-as-absence.
                parent = wsl('ls', '-1', '/sys/fs/cgroup/system.slice')
                if parent.returncode == 0 and self.name not in parent.stdout.splitlines() and wsl('test', '!', '-e', path).returncode == 0:
                    return {'unit': self.name, 'loadState': 'not-found', 'activeState': 'inactive', 'cgroupAbsent': True}
            time.sleep(.05)
        raise RuntimeError('E_UNIT_REMAINS')

    def kill_original(self):
        ctx = self.ready['context']
        props = wsl('systemctl', 'show', self.name, '--property=MainPID,InvocationID,ControlGroup')
        fields = dict(item.split('=', 1) for item in props.stdout.splitlines() if '=' in item)
        check(props.returncode == 0 and ctx['unit'] == self.name and
              fields.get('MainPID') == str(ctx['supervisor']['pid']) and fields.get('InvocationID') == ctx['invocation']
              and fields.get('ControlGroup') == '/system.slice/' + self.name, 'E_UNIT_IDENTITY')
        killed = wsl('systemctl', 'kill', '--kill-whom=all', '--signal=SIGKILL', self.name)
        check(killed.returncode == 0, 'E_KILL')
        self.process.wait(timeout=20)
        check(self.process.returncode != 0, 'E_EXPECTED_CRASH')
        return dict(self.absence(), originalProcess=ctx['supervisor'], invocation=ctx['invocation'],
                    exitCode=self.process.returncode)

    def close(self):
        if self.closed:
            return self.absence()
        try:
            try:
                self.process.stdin.close()
            except (OSError, ValueError):
                pass
            try:
                self.process.wait(timeout=12)
            except subprocess.TimeoutExpired:
                wsl('systemctl', 'stop', self.name)
                self.process.wait(timeout=15)
            return self.absence()
        finally:
            self.thread.join(5)
            check(not self.thread.is_alive(), 'E_CHANNEL_RELAY_REMAINS')
            self.log.close()
            self.output_log.close()
            self.closed = True
