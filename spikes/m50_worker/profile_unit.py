"""Owned supervisor relay for the recovery-ready, fixed VF1 profile."""
import queue
import json
import re
import subprocess
import threading
import time
import uuid

from runtime_candidate.common import require
from spikes.s4f.unit import HIDDEN, ROOT, Unit, WSL, wsl


class ProfileUnit(Unit):
    def __init__(self, role, workspace, anchor, *, check_authority=None):
        require(role in ('original', 'observer', 'replacement'), 'E_ROLE')
        self.name = 'qa-s4-f-' + uuid.uuid4().hex[:16] + '.service'
        translated = wsl('wslpath', '-a', (ROOT / 'spikes/m50_worker/linux_profile.py').as_posix())
        require(translated.returncode == 0 and translated.stdout.startswith('/mnt/'), 'E_WSLCONFIG')
        cmd = WSL + ['systemd-run', '--wait', '--pipe', '--collect', '--unit=' + self.name,
                     '--property=User=phucpn', '--property=Group=phucpn', '--property=Delegate=yes',
                     '--property=DelegateSubgroup=supervisor', '--property=KillMode=control-group',
                     '--property=MemoryMax=768M', '--property=TasksMax=256', '--property=RuntimeMaxSec=240',
                     '/usr/bin/python3', '-I', '-S', '-B', translated.stdout.strip(), role, self.name]
        self.log = (workspace / (self.name + '.stderr')).open('xb')
        self.output_log = (workspace / (self.name + '.stdout')).open('xb')
        self.lines = queue.Queue()
        self.closed = False
        try:
            self.process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.log,
                                            text=True, encoding='utf-8', creationflags=HIDDEN)
        except BaseException:
            self.log.close()
            self.output_log.close()
            raise
        self.thread = threading.Thread(target=self.read_output, daemon=True)
        self.thread.start()
        try:
            self.send(anchor)
            self.ready = self._ready(check_authority)
            require(self.ready.get('ready') and self.ready['unit'] == self.name, self.ready.get('code', 'E_UNIT_START'))
            if role != 'original':
                require(self.ready['context'] == anchor['context'] and
                        self.ready['contextPin'] == anchor['contextPin'], 'E_CONTEXT')
        except BaseException:
            self.close()
            raise

    def _ready(self, check_authority):
        if check_authority is None:
            return self.receive()
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            check_authority()
            try:
                line = self.lines.get(timeout=1)
            except queue.Empty:
                continue
            require(line, 'E_CHANNEL')
            return json.loads(line)
        require(False, 'E_UNIT_START')


class PinnedOriginal:
    """Reopen an original unit's exact identity using the DB-held context only."""
    def __init__(self, resource):
        self.ctx = resource.anchor['context']
        self.name = self.ctx['unit']
        require(re.fullmatch(r'qa-s4-f-[a-f0-9]{16}\.service', self.name), 'E_UNIT_IDENTITY')

    def absence(self):
        result = Unit.absence(self)
        proc = wsl('cat', '/proc/' + str(self.ctx['supervisor']['pid']) + '/stat')
        if proc.returncode == 0:
            stat = proc.stdout.rpartition(') ')[2].split()
            require(len(stat) >= 20 and (stat[0] == 'Z' or stat[19] != self.ctx['supervisor']['startTime']), 'E_PROCESS_LIVE')
        else:
            require(wsl('test', '!', '-e', '/proc/' + str(self.ctx['supervisor']['pid'])).returncode == 0, 'E_PROCESS_LIVE')
        return result

    def kill_original(self):
        props = wsl('systemctl', 'show', self.name, '--property=MainPID,InvocationID,ControlGroup,LoadState')
        fields = dict(item.split('=', 1) for item in props.stdout.splitlines() if '=' in item)
        if fields.get('LoadState') == 'not-found':
            return self.absence()
        require(props.returncode == 0 and fields.get('MainPID') == str(self.ctx['supervisor']['pid'])
                and fields.get('InvocationID') == self.ctx['invocation']
                and fields.get('ControlGroup') == '/system.slice/' + self.name, 'E_UNIT_IDENTITY')
        require(wsl('systemctl', 'kill', '--kill-whom=all', '--signal=SIGKILL', self.name).returncode == 0, 'E_KILL')
        return self.absence()
