"""Read-only candidate discovery, never launches an engine or claims control proof."""
from pathlib import Path
import json
import os
import platform
import shutil
import subprocess
import sys

TOOLS = ('docker', 'podman', 'nerdctl', 'runc', 'crun', 'rootlesskit', 'slirp4netns', 'newuidmap', 'newgidmap')


def engine_gate(observation):
    # Discovery is not image/engine/delegation/enforcement attestation. There is
    # deliberately no accepting launch implementation in this preparation slice.
    return {'launchGate': 'BLOCKED', 'engineExecution': 'NOT RUN',
            'reasonCodes': ['ENGINE_CONTROL_ADAPTER_NOT_IMPLEMENTED'], 'hostFallback': False}


def linux_inventory():
    tools = {name: shutil.which(name) for name in TOOLS}
    common = {str(p): p.is_file() for p in [Path('/usr/bin') / n for n in TOOLS]
              + [Path('/usr/local/bin') / n for n in TOOLS]
              + [Path.home() / '.local/bin' / n for n in ('podman', 'docker', 'nerdctl')]}
    userns = {'status': 'NOT RUN'}
    if Path('/usr/bin/unshare').is_file() and Path('/usr/bin/true').is_file():
        try:
            run = subprocess.run(['/usr/bin/unshare', '-Ur', '/usr/bin/true'], capture_output=True, timeout=5)
            userns = {'status': 'OBSERVED', 'exitCode': run.returncode}
        except (OSError, subprocess.TimeoutExpired):
            userns = {'status': 'ERROR', 'code': 'E_DISCOVERY'}
    cgroup = {'status': 'UNKNOWN'}
    try:
        membership = next(line.split(':', 2)[2] for line in Path('/proc/self/cgroup').read_text().splitlines()
                          if line.startswith('0::'))
        root = Path('/sys/fs/cgroup')
        current = root / membership.lstrip('/')
        cgroup = {'status': 'OBSERVED', 'membership': membership,
                  'rootWritable': os.access(root, os.W_OK), 'currentWritable': os.access(current, os.W_OK),
                  'controllers': (root / 'cgroup.controllers').read_text().split(), 'delegatedEnforcement': 'NOT PROVEN'}
    except (OSError, StopIteration):
        pass
    return {'platform': 'linux', 'python': platform.python_version(), 'kernel': platform.release(), 'uid': os.getuid(),
            'tools': tools, 'commonPaths': common, 'userNamespaceProbe': userns, 'cgroup': cgroup,
            'collectorFlags': {n: hasattr(os, n) for n in ('O_PATH', 'O_NOFOLLOW', 'O_DIRECTORY', 'O_NONBLOCK', 'O_CLOEXEC')},
            **engine_gate(None)}


def inspect_wsl(runner=subprocess.run):
    try:
        # stdin avoids PowerShell/native argv quoting changing $tool or shell quotes.
        result = runner(['wsl.exe', '-d', 'Ubuntu-24.04', '--', 'python3', '-B', '-', '--linux'],
                        input=Path(__file__).read_bytes(), capture_output=True, timeout=25)
        if result.returncode != 0 or len(result.stdout) > 32768:
            raise ValueError('Invalid discovery response')
        value = json.loads(result.stdout)
        if not isinstance(value, dict) or value.get('platform') != 'linux' or value.get('launchGate') != 'BLOCKED':
            raise ValueError('Invalid discovery response')
        return {'status': 'OBSERVED', 'observation': value}
    except (OSError, subprocess.TimeoutExpired, ValueError, TypeError, UnicodeError):
        return {'status': 'UNKNOWN', 'code': 'E_DISCOVERY', **engine_gate(None)}


def windows_inventory():
    common = [r'C:\Program Files\Docker\Docker\resources\bin\docker.exe',
              r'C:\Program Files\RedHat\Podman\podman.exe', r'C:\Program Files\Podman\podman.exe']
    return {'platform': sys.platform, 'python': platform.python_version(),
            'tools': {n: shutil.which(n) for n in ('docker', 'podman', 'nerdctl', 'wsl')},
            'commonPaths': {p: Path(p).is_file() for p in common}, 'wsl': inspect_wsl(), **engine_gate(None)}


if __name__ == '__main__':
    value = linux_inventory() if '--linux' in sys.argv else windows_inventory()
    print(json.dumps(value, indent=2))
    # Internal inventory subprocess succeeds as an observation, never as READY.
    raise SystemExit(0 if '--linux' in sys.argv else 2)
