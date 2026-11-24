"""Private, create-only byte objects in a bootstrap-owned local directory."""
import ctypes
import os
import re
import stat
import sys
import uuid
from contextlib import ExitStack, contextmanager
from functools import wraps
from pathlib import Path
from typing import TypedDict

from .common import Error, canonical, require, sha


MAX_BLOB_BYTES = 8 * 1024 * 1024
MARKER = '.m50-blob-owner-v1'


class BlobRef(TypedDict):
    sha256: str
    byteLength: int


def descriptor(data: bytes) -> BlobRef:
    require(type(data) is bytes and len(data) <= MAX_BLOB_BYTES, 'E_INTEGRITY')
    return {'sha256': sha(data), 'byteLength': len(data)}


def _safe_io(fn):
    @wraps(fn)
    def call(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except (OSError, OverflowError):
            raise Error('E_INTEGRITY') from None
    return call


if os.name == 'nt':
    import msvcrt
    from ctypes import wintypes

    _kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    _create_file = _kernel.CreateFileW
    _create_file.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
                             wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    _create_file.restype = wintypes.HANDLE
    _move_file = _kernel.MoveFileExW
    _move_file.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD]
    _move_file.restype = wintypes.BOOL
    _kernel.CloseHandle.argtypes = [wintypes.HANDLE]

    def _windows_fd(path, *, directory=False, create=False):
        # Pin each directory against rename/delete while resolving its child.
        # OPEN_REPARSE_POINT opens the link itself; reject every reparse kind by handle.
        access = 0x80 if directory else (0x40000000 if create else 0x80000000)
        share = 3 if directory else (0 if create else 1)
        flags = 0x00200000 | (0x02000000 if directory else 0)
        handle = _create_file(str(path), access, share, None, 1 if create else 3, flags, None)
        if handle == ctypes.c_void_p(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            mode = os.O_WRONLY if create else os.O_RDONLY
            return msvcrt.open_osfhandle(handle, mode | os.O_BINARY)
        except BaseException:
            _kernel.CloseHandle(handle)
            raise


def _check_type(fd, *, directory=False):
    info = os.fstat(fd)
    predicate = stat.S_ISDIR if directory else stat.S_ISREG
    require(predicate(info.st_mode) and not getattr(info, 'st_file_attributes', 0)
            & stat.FILE_ATTRIBUTE_REPARSE_POINT, 'E_INTEGRITY')
    if not directory:
        require(info.st_nlink == 1, 'E_INTEGRITY')
    return info


class _Directory:
    def __init__(self, path, fd):
        self.path = path
        self.fd = fd

    def mkdir(self, name):
        if os.name == 'nt':
            os.mkdir(self.path / name, 0o700)
        else:
            os.mkdir(name, 0o700, dir_fd=self.fd)

    def sync(self):
        if os.name != 'nt':
            os.fsync(self.fd)

    def file(self, name, *, create=False):
        if os.name == 'nt':
            fd = _windows_fd(self.path / name, create=create)
        else:
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL if create else os.O_RDONLY
            fd = os.open(name, flags | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=self.fd)
        try:
            _check_type(fd)
            return os.fdopen(fd, 'wb' if create else 'rb')
        except BaseException:
            os.close(fd)
            raise

    def publish(self, source, dest):
        if os.name == 'nt':
            # WRITE_THROUGH, without REPLACE_EXISTING. Same-volume rename of flushed bytes.
            if not _move_file(str(self.path / source), str(self.path / dest), 8):
                raise ctypes.WinError(ctypes.get_last_error())
        else:
            # Linux RENAME_NOREPLACE. Fail closed on unsupported filesystems.
            require(sys.platform == 'linux', 'E_INTEGRITY')
            rename = getattr(ctypes.CDLL(None, use_errno=True), 'renameat2', None)
            require(rename is not None, 'E_INTEGRITY')
            if rename(self.fd, source.encode('ascii'), self.fd, dest.encode('ascii'), 1) != 0:
                err = ctypes.get_errno()
                raise OSError(err, os.strerror(err))

    def unlink_stage(self, name):
        if os.name == 'nt':
            (self.path / name).unlink()
        else:
            os.unlink(name, dir_fd=self.fd)


@contextmanager
def _directory(path):
    """Walk from the volume root with pinned handles; never resolve through a symlink."""
    require(path.is_absolute() and '..' not in path.parts, 'E_INTEGRITY')
    if os.name == 'nt':
        require(re.fullmatch(r'[A-Za-z]:', path.drive), 'E_INTEGRITY')
    with ExitStack() as stack:
        location = Path(path.anchor)
        fd = None
        for index, part in enumerate(path.parts):
            if index:
                location = location / part
            if os.name == 'nt':
                fd = _windows_fd(location, directory=True)
            else:
                fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            stack.callback(os.close, fd)
            _check_type(fd, directory=True)
        yield _Directory(path, fd)


def _marker(directory, owner):
    info = os.fstat(directory.fd)
    return canonical({'format': 'm50-private-blobs-v1', 'owner': owner,
                      'path': os.path.normcase(str(directory.path)),
                      'device': info.st_dev, 'inode': info.st_ino})


def _validate_root(root, owner):
    path = Path(root)
    require(path.is_absolute() and path != Path(path.anchor) and '..' not in path.parts
            and isinstance(owner, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,128}', owner), 'E_INTEGRITY')
    return path


def _write(stream, raw):
    require(stream.write(raw) == len(raw), 'E_INTEGRITY')
    stream.flush()
    os.fsync(stream.fileno())


class BlobStore:
    """Trusted bootstrap supplies root/owner. DB callers supply immutable byte references."""
    @classmethod
    @_safe_io
    def create(cls, root: Path, *, owner: str):
        path = _validate_root(root, owner)
        with _directory(path.parent) as parent:
            parent.mkdir(path.name)  # Never adopt or overwrite an existing directory.
            parent.sync()
            with _directory(path) as directory:
                with directory.file(MARKER, create=True) as marker:
                    _write(marker, _marker(directory, owner))
                directory.sync()
        return cls(path, owner=owner)

    @_safe_io
    def __init__(self, root: Path, *, owner: str):
        self._root = _validate_root(root, owner)
        self._owner = owner
        with _directory(self._root) as directory:
            self._expected_marker = _marker(directory, owner)
        with self._bound():
            pass

    @contextmanager
    def _bound(self):
        with _directory(self._root) as directory, directory.file(MARKER) as marker:
            expected = _marker(directory, self._owner)
            require(expected == self._expected_marker and marker.read(len(expected) + 1) == expected,
                    'E_INTEGRITY')
            yield directory

    @staticmethod
    def _read(directory, ref):
        with directory.file(ref['sha256']) as stream:
            expected = ref['byteLength']
            require(os.fstat(stream.fileno()).st_size == expected, 'E_INTEGRITY')
            raw = stream.read(expected + 1)
            require(len(raw) == expected and sha(raw) == ref['sha256'], 'E_INTEGRITY')
            return raw

    @_safe_io
    def put(self, raw: bytes) -> BlobRef:
        ref = descriptor(raw)
        with self._bound() as directory:
            stage = '.stage-' + uuid.uuid4().hex
            writer = directory.file(stage, create=True)
            owned_stage = True
            try:
                with writer:
                    _write(writer, raw)
                try:
                    directory.publish(stage, ref['sha256'])
                    owned_stage = False
                except FileExistsError:
                    pass  # Verify existing bytes before acknowledging a duplicate.
                require(self._read(directory, ref) == raw, 'E_INTEGRITY')
                directory.sync()
            finally:
                if owned_stage:
                    directory.unlink_stage(stage)
        return ref

    @_safe_io
    def get(self, ref: BlobRef) -> bytes:
        require(isinstance(ref, dict) and set(ref) == {'sha256', 'byteLength'}
                and isinstance(ref['sha256'], str) and re.fullmatch('[0-9a-f]{64}', ref['sha256'])
                and type(ref['byteLength']) is int and 0 <= ref['byteLength'] <= MAX_BLOB_BYTES, 'E_INTEGRITY')
        with self._bound() as directory:
            return self._read(directory, ref)
