"""Windows pipe adapter to a private delegated S4-E Linux supervisor."""
from pathlib import Path
import json
import queue
import subprocess
import threading
import uuid

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / '.cache/s6/s4-e'


class Helper:
    def __init__(self):
        CACHE.mkdir(parents=True, exist_ok=True)
        self.unit = 'qa-s4-e-' + uuid.uuid4().hex[:12]
        linux_root = subprocess.check_output(['wsl.exe', '-d', 'Ubuntu-24.04', '--', 'wslpath', '-a', ROOT.as_posix()], text=True).strip()
        self.argv = ['wsl.exe', '-d', 'Ubuntu-24.04', '-u', 'root', '--', 'systemd-run', '--unit=' + self.unit, '--wait', '--pipe', '--collect', '--property=User=phucpn', '--property=Group=phucpn', '--property=Delegate=yes', '--property=DelegateSubgroup=supervisor', '--property=MemoryMax=512M', '--property=TasksMax=256', '--property=RuntimeMaxSec=240', '/usr/bin/python3', '-B', linux_root + '/spikes/s4e/engine_helper.py']
        self.stderr_path = CACHE / (self.unit + '-stderr.log')
        self.stderr = self.stderr_path.open('xb')
        self.proc = subprocess.Popen(self.argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.stderr, text=True, encoding='utf-8', creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        self.lines = queue.Queue(); self.broken = False
        def reader():
            for line in self.proc.stdout: self.lines.put(line)
            self.lines.put(None)
        threading.Thread(target=reader, daemon=True).start()
        try:
            self.ready = self.receive()
            if not self.ready.get('ready') or self.ready.get('hostUid') != 1000: raise RuntimeError('E_HELPER_READY')
            self.generation = self.ready['generation']
        except Exception:
            self._stop_unit()
            self.stderr.close()
            raise

    def receive(self):
        try:
            line = self.lines.get(timeout=40)
            if line is None: raise RuntimeError('E_EOF')
            return json.loads(line)
        except Exception:
            self.broken = True
            raise RuntimeError('E_HELPER_CHANNEL') from None

    def request(self, op, **body):
        if self.broken: raise RuntimeError('E_HELPER_CHANNEL')
        try:
            self.proc.stdin.write(json.dumps({'op': op, **body}) + '\n'); self.proc.stdin.flush()
        except (OSError, ValueError):
            self.broken = True; raise RuntimeError('E_HELPER_CHANNEL') from None
        reply = self.receive()
        if not reply.get('ok'): raise RuntimeError(reply.get('code', 'E_HELPER'))
        return reply['result']

    def _stop_unit(self):
        subprocess.run(['wsl.exe', '-d', 'Ubuntu-24.04', '-u', 'root', '--', 'systemctl', 'stop', self.unit], capture_output=True, timeout=20)
        try: self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill(); self.proc.wait(timeout=10)

    def close(self):
        error = None; closed = None
        try:
            self.proc.stdin.close()
            closed = self.receive()
            self.proc.wait(timeout=30)
            if self.proc.returncode != 0 or not closed.get('closed'): error = 'E_HELPER_CLOSE'
        except Exception as exc:
            error = 'E_HELPER_CLOSE: ' + str(exc)
        finally:
            if self.proc.poll() is None:
                try: self._stop_unit()
                except Exception as exc: error = (error or 'E_HELPER_CLOSE') + '; stop: ' + str(exc)
            self.stderr.close()
        result = subprocess.run(['wsl.exe', '-d', 'Ubuntu-24.04', '--', 'systemctl', 'show', self.unit, '--property=LoadState'], capture_output=True, text=True, timeout=10)
        absent = subprocess.run(['wsl.exe', '-d', 'Ubuntu-24.04', '--', 'test', '!', '-e', '/sys/fs/cgroup/system.slice/' + self.unit + '.service'], timeout=10).returncode == 0
        if 'LoadState=not-found' not in result.stdout or not absent: error = (error or 'E_HELPER_CLOSE') + '; E_UNIT_REMAINS'
        if error: raise RuntimeError(error)
        return {'unit': self.unit, 'loadStateNotFound': True, 'cgroupAbsent': True, 'helperExit': self.proc.returncode, 'cleanup': closed['cleanup']}
