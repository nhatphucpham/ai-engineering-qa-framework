"""Private, rootless, isolated-storage Podman fixture; never a product executor API."""
from pathlib import Path
import hashlib
import io
import json
import os
import re
import subprocess
import tarfile
import tempfile
import uuid


class RootlessEngine:
    def __init__(self):
        if os.getuid() != 1000:
            raise RuntimeError('E_ROOTLESS_UID')
        membership = next(x.split(':', 2)[2] for x in Path('/proc/self/cgroup').read_text().splitlines() if x.startswith('0::'))
        current = Path('/sys/fs/cgroup') / membership.lstrip('/')
        if current.name != 'supervisor' or not current.parent.name.startswith('qa-s4-'):
            raise RuntimeError('E_DELEGATION')
        self.parent = current.parent
        (self.parent / 'cgroup.subtree_control').write_text('+cpu +memory +pids')
        self.container_parent = self.parent / 'containers'
        self.container_parent.mkdir(exist_ok=True)
        self.base = Path(tempfile.mkdtemp(prefix='qa-s4-engine-'))
        (self.base / 'marker.json').write_text(json.dumps({'kind': 'qa-s4-private-engine-v1', 'uid': os.getuid()}))
        for name in ('home', 'runtime', 'storage', 'runroot', 'config', 'data', 'cache', 'output', 'input'):
            (self.base / name).mkdir(mode=0o700)
        self.auth = self.base / 'auth.json'; self.auth.write_text('{"auths":{}}')
        config = self.base / 'containers.conf'
        config.write_text('[engine]\ncgroup_manager="cgroupfs"\nevents_logger="file"\nruntime="crun"\n[network]\nnetwork_backend="cni"\n')
        self.env = {'PATH': '/usr/bin:/bin', 'HOME': str(self.base / 'home'),
                    'XDG_RUNTIME_DIR': str(self.base / 'runtime'), 'XDG_CONFIG_HOME': str(self.base / 'config'),
                    'XDG_DATA_HOME': str(self.base / 'data'), 'XDG_CACHE_HOME': str(self.base / 'cache'),
                    'REGISTRY_AUTH_FILE': str(self.auth), 'CONTAINERS_CONF': str(config), 'LANG': 'C.UTF-8'}
        self.prefix = ['/usr/bin/podman', '--root', str(self.base / 'storage'), '--runroot', str(self.base / 'runroot'),
                       '--storage-driver=vfs', '--cgroup-manager=cgroupfs', '--events-backend=file', '--runtime=/usr/bin/crun']
        self.owned = []
        info = json.loads(self.command(['info', '--format=json']).stdout)
        if not info['host']['security']['rootless']:
            raise RuntimeError('E_ROOTLESS_INFO')
        self.info = info

    def command(self, args, *, check=True, timeout=30):
        result = subprocess.run(self.prefix + args, env=self.env, capture_output=True, text=True, timeout=timeout)
        if check and result.returncode:
            raise RuntimeError('E_PODMAN_COMMAND: ' + result.stderr[-1500:])
        return result

    def build_image(self):
        binary = Path('/usr/bin/busybox').read_bytes()
        archive = self.base / 'rootfs.tar'
        with tarfile.open(archive, 'w') as package:
            for directory in ('bin', 'etc', 'tmp', 'input', 'output'):
                entry = tarfile.TarInfo(directory); entry.type = tarfile.DIRTYPE
                entry.mode = 0o1777 if directory == 'tmp' else 0o755; package.addfile(entry)
            files = {'bin/busybox': binary, 'etc/passwd': b'qa:x:1000:1000:QA:/tmp:/bin/sh\n', 'etc/group': b'qa:x:1000:\n'}
            for name, data in files.items():
                entry = tarfile.TarInfo(name); entry.size = len(data); entry.mode = 0o755 if name.endswith('busybox') else 0o644
                package.addfile(entry, io.BytesIO(data))
            for applet in ('sh', 'id', 'touch', 'cat', 'ls', 'sleep', 'ip', 'wget', 'awk', 'dd', 'head', 'printf',
                           'seq', 'true', 'false', 'mkdir', 'ps', 'kill', 'yes', 'wc', 'grep', 'cut'):
                entry = tarfile.TarInfo('bin/' + applet); entry.type = tarfile.SYMTYPE; entry.linkname = 'busybox'; entry.mode = 0o777
                package.addfile(entry)
        imported = self.command(['import', '--change', 'USER 1000:1000', str(archive), 'localhost/qa-s4-fixture:v1'])
        self.image = imported.stdout.strip()
        if not re.fullmatch('sha256:[a-f0-9]{64}', self.image):
            raise RuntimeError('E_IMAGE_PIN')
        image = json.loads(self.command(['image', 'inspect', self.image]).stdout)[0]
        if image['Id'].removeprefix('sha256:') != self.image.removeprefix('sha256:'):
            raise RuntimeError('E_IMAGE_ID')
        return {'imageId': self.image, 'busyboxSha256': hashlib.sha256(binary).hexdigest(),
                'rootfsTarSha256': hashlib.sha256(archive.read_bytes()).hexdigest(), 'source': 'signed Ubuntu busybox-static local fixture'}

    def launch(self, command, *, memory='64m', pids=32, cpus='0.5'):
        name = 'qa-s4-' + uuid.uuid4().hex
        args = ['run', '-d', '--pull=never', '--name', name, '--label', 'qa.s4.owner=private-fixture',
                '--userns=keep-id', '--user=1000:1000', '--read-only', '--read-only-tmpfs=false',
                '--cap-drop=all', '--security-opt=no-new-privileges', '--network=none',
                '--memory', memory, '--memory-swap', memory, '--pids-limit', str(pids), '--cpus', cpus,
                '--cgroup-parent', str(self.container_parent).removeprefix('/sys/fs/cgroup'),
                '--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=8m,mode=1777',
                '--volume', str(self.base / 'input') + ':/input:ro', '--volume', str(self.base / 'output') + ':/output:rw',
                self.image, '/bin/sh', '-c', command]
        result = self.command(args)
        container = result.stdout.strip()
        self.owned.append(container)
        return container

    def inspect(self, container):
        if container not in self.owned:
            raise RuntimeError('E_CONTAINER_SCOPE')
        return json.loads(self.command(['inspect', container]).stdout)[0]

    def cgroup(self, container):
        pid = self.inspect(container)['State']['Pid']
        membership = next(x.split(':', 2)[2] for x in Path('/proc/' + str(pid) + '/cgroup').read_text().splitlines() if x.startswith('0::'))
        path = Path('/sys/fs/cgroup') / membership.lstrip('/')
        if not path.is_relative_to(self.container_parent):
            raise RuntimeError('E_CONTAINER_CGROUP')
        return path

    def cleanup(self):
        observations = []
        for container in list(self.owned):
            self.command(['rm', '--force', container])
            observations.append({'containerId': container, 'removed': self.command(['inspect', container], check=False).returncode != 0})
        self.owned.clear()
        remaining = json.loads(self.command(['ps', '--all', '--format=json']).stdout)
        if remaining:
            raise RuntimeError('E_OWNED_CLEANUP')
        return {'containers': observations, 'privateStorageEmptyOfContainers': True, 'retainedMarkedCache': str(self.base)}
