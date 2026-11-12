"""Private Linux FD collector; all raw output restricted, no engine/auth/export API."""
from dataclasses import dataclass, field
import hashlib
import os
import re
import stat
import sys
import threading
import time

VERSION = 's4-collector-1.0.0'


class Blocked(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def capabilities():
    return (sys.platform == 'linux' and os.open in os.supports_dir_fd
            and all(hasattr(os, n) for n in ('O_PATH', 'O_NOFOLLOW', 'O_DIRECTORY', 'O_NONBLOCK', 'O_CLOEXEC'))
            and os.path.isdir('/proc/self/fd'))


def positive(value, maximum):
    if type(value) is not int or not 1 <= value <= maximum:
        raise Blocked('E_INPUT')


def parts(relative):
    if (type(relative) is not str or not relative or len(relative.encode('utf-8')) > 2048
            or '\\' in relative or '\x00' in relative):
        raise Blocked('E_PATH')
    values = relative.split('/')
    if len(values) > 16 or any(not p or p in ('.', '..') or len(p.encode('utf-8')) > 255 for p in values):
        raise Blocked('E_PATH')
    return values


def fingerprint(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_nlink, info.st_mtime_ns, info.st_ctime_ns)


@dataclass(repr=False)
class RestrictedBlob:
    manifest: dict
    _payload: bytes = field(repr=False)

    def __repr__(self):
        return '<RestrictedBlob restricted_raw_output>'

    def private_bytes(self):
        """Trusted operator memory only; never route through QA/read/export APIs."""
        return self._payload


class PrivateCollector:
    def __init__(self, root_fd, expected_root, scope, *, max_bytes=1048576, max_total=4194304, max_files=16, max_ms=1000):
        if not capabilities():
            raise Blocked('E_CAPABILITY')
        positive(max_bytes, 16 * 1048576); positive(max_total, 64 * 1048576)
        positive(max_files, 1024); positive(max_ms, 5000)
        if (type(root_fd) is not int or root_fd < 0 or type(expected_root) is not tuple or len(expected_root) != 2
                or not all(type(v) is int and v >= 0 for v in expected_root)):
            raise Blocked('E_CONTEXT')
        if (type(scope) is not dict or set(scope) != {'projectId', 'runId', 'assignmentId', 'attempt', 'fence'}
                or not all(type(scope[k]) is str and re.fullmatch('[A-Za-z0-9_-]{1,64}', scope[k])
                           for k in ('projectId', 'runId', 'assignmentId'))):
            raise Blocked('E_CONTEXT')
        positive(scope['attempt'], 2**63 - 1); positive(scope['fence'], 2**63 - 1)
        fd = None
        try:
            fd = os.dup(root_fd)
            info = os.fstat(fd)
            if not stat.S_ISDIR(info.st_mode) or (info.st_dev, info.st_ino) != expected_root:
                raise Blocked('E_CONTEXT')
        except Blocked:
            if fd is not None:
                os.close(fd)
            raise
        except OSError:
            if fd is not None:
                os.close(fd)
            raise Blocked('E_CONTEXT') from None
        self.root_fd = fd
        self._lock = threading.Lock()
        self.anchor = expected_root
        self.scope = dict(scope)
        self.max_bytes, self.max_total, self.max_files, self.max_ms = max_bytes, max_total, max_files, max_ms
        self.total = self.files = 0

    def close(self):
        with self._lock:
            if self.root_fd is not None:
                os.close(self.root_fd)
                self.root_fd = None

    @staticmethod
    def qa_content(role, channel, **labels):
        raise Blocked('E_RESTRICTED')

    def collect_private(self, relative, *, after_directory=lambda: None, after_pin=lambda: None, after_chunk=lambda: None):
        """Fault hooks are trusted test host callbacks, not request/manifest fields."""
        with self._lock:
            return self._collect_private(relative, after_directory, after_pin, after_chunk)

    def _collect_private(self, relative, after_directory, after_pin, after_chunk):
        opened = []
        try:
            components = parts(relative)
            if self.root_fd is None:
                raise Blocked('E_CONTEXT')
            if self.files >= self.max_files:
                raise Blocked('E_BUDGET')
            end = time.monotonic() + self.max_ms / 1000

            def deadline():
                if time.monotonic() >= end:
                    raise Blocked('E_TIMEOUT')

            directory = os.dup(self.root_fd); opened.append(directory)
            root = os.fstat(directory)
            if (root.st_dev, root.st_ino) != self.anchor:
                raise Blocked('E_CONTEXT')
            for component in components[:-1]:
                deadline()
                directory = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=directory)
                opened.append(directory)
                if os.fstat(directory).st_dev != self.anchor[0]:
                    raise Blocked('E_SCOPE')
            after_directory(); deadline()
            pinned = os.open(components[-1], os.O_PATH | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=directory)
            opened.append(pinned)
            before = os.fstat(pinned)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
                raise Blocked('E_TYPE')
            if before.st_dev != self.anchor[0]:
                raise Blocked('E_SCOPE')
            if before.st_size > self.max_bytes or self.total + before.st_size > self.max_total:
                raise Blocked('E_SIZE')
            after_pin(); deadline()
            reader = os.open('/proc/self/fd/' + str(pinned), os.O_RDONLY | os.O_NONBLOCK | os.O_CLOEXEC)
            opened.append(reader)
            if fingerprint(os.fstat(reader)) != fingerprint(before):
                raise Blocked('E_CHANGED')
            chunks, count = [], 0
            while True:
                deadline()
                chunk = os.read(reader, min(65536, self.max_bytes - count + 1))
                deadline()
                if not chunk:
                    break
                count += len(chunk)
                if count > self.max_bytes or self.total + count > self.max_total:
                    raise Blocked('E_SIZE')
                chunks.append(chunk); after_chunk(); deadline()
            after = os.fstat(reader)
            if fingerprint(before) != fingerprint(after) or count != after.st_size:
                raise Blocked('E_CHANGED')
            payload = b''.join(chunks)
            self.files += 1; self.total += count
            manifest = {'collectorVersion': VERSION, 'classification': 'restricted_raw_output',
                        'scope': dict(self.scope), 'byteLength': count, 'sha256': hashlib.sha256(payload).hexdigest(),
                        'rootIdentity': list(self.anchor), 'fileIdentity': [after.st_dev, after.st_ino],
                        'snapshotGuarantee': 'observed_stable_only', 'ordinaryRelease': 'DENIED'}
            return RestrictedBlob(manifest, payload)
        except Blocked:
            raise
        except (OSError, ValueError, TypeError, UnicodeError):
            raise Blocked('E_COLLECTION') from None
        finally:
            for fd in reversed(opened):
                os.close(fd)
