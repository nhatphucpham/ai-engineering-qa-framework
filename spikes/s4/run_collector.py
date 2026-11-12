"""Linux-only real-filesystem collector probes; actual engine controls remain NOT RUN."""
from pathlib import Path
import base64
import contextlib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import io
import json
import os
import platform
import re
import select
import signal
import socket
import sys
import tempfile
import threading
import time
import traceback
from unittest.mock import patch

from collector import PrivateCollector, Blocked, capabilities
from preflight import linux_inventory, engine_gate

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / '.cache/s6/s4-a'
SCOPE = {'projectId': 'syntheticA', 'runId': 'runA', 'assignmentId': 'assignmentA', 'attempt': 1, 'fence': 1}


def require(value, message):
    if not value:
        raise AssertionError(message)


def blocked(action, codes):
    try:
        action()
    except Blocked as error:
        require(error.code in codes, 'Unexpected safe error category')
        return error.code
    raise AssertionError('Expected private collection denial')


class Fixture:
    def __init__(self):
        self.temp = tempfile.TemporaryDirectory(prefix='s4-collector-')
        self.base = Path(self.temp.name)
        self.root = self.base / 'output'; self.root.mkdir(mode=0o700)
        self.outside = self.base / 'outside'; self.outside.mkdir(mode=0o700)
        self.fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        info = os.fstat(self.fd); self.anchor = (info.st_dev, info.st_ino)

    @contextlib.contextmanager
    def collector(self, **limits):
        collector = PrivateCollector(self.fd, self.anchor, SCOPE, **limits)
        try:
            yield collector
        finally:
            collector.close()

    def close(self):
        os.close(self.fd); self.temp.cleanup()


def type_probe(f, relative):
    # Harness guard only; not a product stalled-IO termination/cleanup claim.
    reader, writer = os.pipe()
    pid = os.fork()
    if pid == 0:
        os.close(reader)
        try:
            with f.collector() as c:
                code = blocked(lambda: c.collect_private(relative), ('E_TYPE', 'E_COLLECTION'))
            os.write(writer, code.encode('ascii'))
            os._exit(0)
        except Exception:
            os._exit(2)
    os.close(writer)
    try:
        ready, _, _ = select.select([reader], [], [], 2)
        if not ready:
            os.kill(pid, signal.SIGKILL); os.waitpid(pid, 0)
            raise AssertionError('Special-file probe hung')
        code = os.read(reader, 64).decode('ascii')
        _, status = os.waitpid(pid, 0)
        require(os.waitstatus_to_exitcode(status) == 0 and code in ('E_TYPE', 'E_COLLECTION'), 'Special-file probe failed')
        return code
    finally:
        os.close(reader)


def experiment(evidence, forbidden):
    require(capabilities() and os.getuid() != 0, 'Linux collector capability/nonroot fixture prerequisites missing')
    checks = evidence['checks'] = {}
    observation = linux_inventory()
    require(engine_gate({'ready': True})['launchGate'] == 'BLOCKED', 'Discovery enabled launch')
    checks['F01'] = {'status': 'PASS', 'launchGate': 'BLOCKED', 'engineExecution': 'NOT RUN',
                     'collectorLinuxCapable': True, 'inventory': observation}
    f = Fixture()
    canary = b'synthetic-private-' + os.urandom(32)
    external = b'synthetic-external-' + os.urandom(32)
    forbidden.extend((canary, external))
    try:
        (f.root / 'normal').write_bytes(canary)
        (f.root / 'nested').mkdir(); (f.root / 'nested/Unicode-猫').write_bytes('synthetic Tiếng Việt'.encode())
        (f.root / 'empty').write_bytes(b'')
        with f.collector() as c:
            result = c.collect_private('normal')
            require(result.private_bytes() == canary and result.manifest['sha256'] == hashlib.sha256(canary).hexdigest(), 'Private bytes/hash mismatch')
            require(result.manifest['byteLength'] == len(canary) and result.manifest['ordinaryRelease'] == 'DENIED', 'Manifest classification mismatch')
            SCOPE['runId'] = 'mutatedCaller'
            require(result.manifest['scope']['runId'] == 'runA', 'Scope not detached')
            SCOPE['runId'] = 'runA'
            require(c.collect_private('empty').manifest['byteLength'] == 0, 'Empty file not collected')
            require(c.collect_private('nested/Unicode-猫').private_bytes() == 'synthetic Tiếng Việt'.encode(), 'Unicode path/content mismatch')
        blocked(lambda: PrivateCollector(f.fd, (f.anchor[0], f.anchor[1] + 1), SCOPE), ('E_CONTEXT',))
        closed = os.dup(f.fd); os.close(closed)
        before = len(os.listdir('/proc/self/fd'))
        blocked(lambda: PrivateCollector(closed, f.anchor, SCOPE), ('E_CONTEXT',))
        with patch('collector.os.fstat', side_effect=OSError('synthetic private detail')):
            blocked(lambda: PrivateCollector(f.fd, f.anchor, SCOPE), ('E_CONTEXT',))
        require(len(os.listdir('/proc/self/fd')) == before, 'Constructor failure leaked descriptor')
        checks['F02'] = {'status': 'PASS', 'private_regular_empty_nested_unicode_hash_length': True,
                         'root_identity_checked_scope_detached': True,
                         'closed_FD_and_fstat_failure_fixed_error_no_FD_leak': True}

        (f.outside / 'secret').write_bytes(external)
        os.symlink(f.outside / 'secret', f.root / 'link')
        os.symlink(f.outside, f.root / 'dirlink')
        paths = ('../outside/secret', '/etc/passwd', './normal', 'nested//file', '', 'nested/../normal',
                 'nested\\normal', '\x00', 'a' * 256, 'a/' * 17 + 'file')
        with f.collector() as c:
            for value in paths:
                blocked(lambda: c.collect_private(value), ('E_PATH',))
            for value in ('link', 'dirlink/secret'):
                blocked(lambda: c.collect_private(value), ('E_TYPE', 'E_COLLECTION'))
        checks['F03'] = {'status': 'PASS', 'invalid_path_cases': len(paths), 'leaf_and_directory_symlink_denied': True}

        os.mkfifo(f.root / 'fifo')
        unix = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            unix.bind(str(f.root / 'socket'))
            os.link(f.outside / 'secret', f.root / 'hardlink')
            codes = {name: type_probe(f, name) for name in ('fifo', 'socket', 'nested', 'hardlink')}
        finally:
            unix.close()
        (f.root / 'swapType').write_bytes(canary)
        with f.collector() as c:
            def fifo_swap():
                (f.root / 'swapType').unlink(); os.mkfifo(f.root / 'swapType')
            blocked(lambda: c.collect_private('swapType', after_directory=fifo_swap), ('E_TYPE',))
        checks['F04'] = {'status': 'PASS', 'actual_special_file_denials': codes,
                         'regular_to_FIFO_before_pin_denied': True, 'two_second_harness_hang_guard': True}

        (f.root / 'swapParent').mkdir(); (f.root / 'swapParent/item').write_bytes(canary)
        (f.outside / 'item').write_bytes(external)
        with f.collector() as c:
            def parent_swap():
                os.rename(f.root / 'swapParent', f.root / 'originalParent')
                os.symlink(f.outside, f.root / 'swapParent')
            pinned = c.collect_private('swapParent/item', after_directory=parent_swap)
            require(pinned.private_bytes() == canary and pinned.private_bytes() != external, 'Parent swap escaped pinned directory')
        (f.root / 'swapLeaf').write_bytes(canary)
        with f.collector() as c:
            def leaf_swap():
                (f.root / 'swapLeaf').unlink(); os.symlink(f.outside / 'secret', f.root / 'swapLeaf')
            blocked(lambda: c.collect_private('swapLeaf', after_pin=leaf_swap), ('E_CHANGED',))
        checks['F05'] = {'status': 'PASS', 'parent_rename_symlink_swap_stays_on_original_FD': True,
                         'pinned_leaf_unlink_replace_observed_denied': True, 'external_canary_not_returned': True}

        (f.root / 'large').write_bytes(b'x' * 100)
        (f.root / 'four').write_bytes(b'1234')
        with f.collector(max_bytes=10) as c:
            blocked(lambda: c.collect_private('large'), ('E_SIZE',))
            require(c.total == c.files == 0, 'Failed operation consumed returned-object budgets')
        with f.collector(max_total=6) as c:
            c.collect_private('four'); blocked(lambda: c.collect_private('four'), ('E_SIZE',))
        with f.collector(max_files=1) as c:
            c.collect_private('empty'); blocked(lambda: c.collect_private('empty'), ('E_BUDGET',))
        with f.collector(max_total=6) as c:
            gate = threading.Barrier(2)
            def concurrent_collect():
                gate.wait(timeout=2)
                try:
                    c.collect_private('four')
                    return 'accepted'
                except Blocked as error:
                    return error.code
            with ThreadPoolExecutor(max_workers=2) as pool:
                jobs = [pool.submit(concurrent_collect) for _ in range(2)]
                outcomes = sorted(job.result(timeout=3) for job in jobs)
            require(outcomes == ['E_SIZE', 'accepted'] and c.total == 4 and c.files == 1, 'Concurrent collector exceeded shared budget')
        for mutation in ('grow', 'replace_same_size'):
            (f.root / 'mutation').write_bytes(b'm' * 100)
            changed = []
            def mutate_once():
                if not changed:
                    with (f.root / 'mutation').open('ab' if mutation == 'grow' else 'r+b') as stream:
                        stream.write(b'X')
                    changed.append(True)
            with f.collector() as c:
                blocked(lambda: c.collect_private('mutation', after_chunk=mutate_once), ('E_CHANGED',))
                require(c.total == c.files == 0 and changed == [True], 'Mutation returned partial bytes or accounting')
        checks['F06'] = {'status': 'PASS', 'file_total_count_caps_enforced': True,
                         'two_concurrent_calls_one_accept_with_shared_total_budget': True,
                         'actual_growth_and_same_size_write_observed_denied': True, 'failed_calls_no_payload_or_budget_commit': True}

        with f.collector(max_ms=50) as c:
            reached = []
            def slow():
                reached.append(True); time.sleep(.08)
            blocked(lambda: c.collect_private('normal', after_directory=slow), ('E_TIMEOUT',))
            require(reached == [True] and c.files == 0, 'Cooperative deadline probe did not reach hook')
        with patch('collector.capabilities', return_value=False):
            blocked(lambda: PrivateCollector(f.fd, f.anchor, SCOPE), ('E_CAPABILITY',))
        checks['F07'] = {'status': 'PASS', 'actual_cooperative_deadline_crossing_denied': True,
                         'missing_capability_denied': True, 'hard_syscall_timeout_and_cleanup': 'NOT RUN'}

        calls = 0
        for role in ('Admin', 'Owner', 'Runner', 'Viewer'):
            for channel in ('read', 'export', 'stream', 'attachment', 'source'):
                blocked(lambda: PrivateCollector.qa_content(role, channel, authorized=True, sanitized=True), ('E_RESTRICTED',))
                calls += 1
        before_fds = len(os.listdir('/proc/self/fd'))
        with f.collector() as c:
            during_fds = len(os.listdir('/proc/self/fd'))
            for _ in range(100):
                blocked(lambda: c.collect_private('link'), ('E_TYPE',))
                blocked(lambda: c.collect_private('../outside/secret'), ('E_PATH',))
            require(len(os.listdir('/proc/self/fd')) == during_fds, 'Failure descriptor leak')
        require(len(os.listdir('/proc/self/fd')) == before_fds, 'Root duplicate descriptor leak')
        require(all(t not in repr(result).encode() and base64.b64encode(t) not in repr(result).encode()
                    and t.hex().encode() not in repr(result).encode() for t in forbidden), 'Raw data in representation')
        checks['F08'] = {'status': 'PASS', 'all_role_channel_raw_denials': calls, 'fake_labels_cannot_enable_release': True,
                         '200_failure_calls_no_FD_leak': True, 'private_blob_repr_safe': True}
    finally:
        f.close()


def inputs():
    paths = [p for p in (ROOT / 'spikes/s4').rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    paths += [ROOT / 'docs/S4-A-PROTOCOL.md']
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


def main():
    if len(sys.argv) != 3 or not re.fullmatch('[a-f0-9]{40}', sys.argv[2]):
        raise SystemExit('Use fresh docs/s4-results/<id>.json and caller-held baseline hash')
    dest = (ROOT / sys.argv[1]).resolve()
    if dest.parent != (ROOT / 'docs/s4-results').resolve() or dest.exists() or dest.suffix != '.json':
        raise SystemExit('Use new S4 evidence path')
    CACHE.mkdir(parents=True, exist_ok=True)
    evidence = {'evidenceVersion': 's4-a-1.0.0', 'classification': 'synthetic-only', 'baseline': sys.argv[2],
                'baselineSource': 'caller-held Windows git rev-parse HEAD', 'python': platform.python_version(),
                'platform': sys.platform, 'kernel': platform.release(), 'uid': os.getuid(),
                'startedAt': datetime.now(timezone.utc).isoformat(), 'inputsBefore': inputs(), 'status': 'RUNNING',
                'limits': ['Private Linux filesystem subset, no container/engine launch/network/resource/cleanup proof',
                           'No authenticated IAP-B/broker/encrypted quarantine/ordinary release integration',
                           'Cooperative deadline only, no hard stalled-syscall timeout or atomic snapshot guarantee']}
    begin = time.monotonic(); forbidden = []; stdout = io.StringIO(); stderr = io.StringIO()
    try:
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            experiment(evidence, forbidden)
        raw = (stdout.getvalue() + stderr.getvalue()).encode()
        require(all(t not in raw and base64.b64encode(t) not in raw and t.hex().encode() not in raw for t in forbidden), 'Canary in emitted diagnostics')
        evidence['diagnostics'] = {'stdoutBytes': len(stdout.getvalue()), 'stderrBytes': len(stderr.getvalue()), 'raw_base64_hex_scan': 'PASS'}
        evidence['inputsAfter'] = inputs(); require(evidence['inputsBefore'] == evidence['inputsAfter'], 'Inputs changed')
        evidence['status'] = 'PASS'
    except Exception as error:
        evidence['status'] = 'ERROR'; evidence['errorType'] = type(error).__name__
        (CACHE / 'collector-last-error.txt').write_text(traceback.format_exc(), encoding='utf-8')
    evidence['elapsedSeconds'] = time.monotonic() - begin; evidence['finishedAt'] = datetime.now(timezone.utc).isoformat()
    encoded = json.dumps(evidence, indent=2).encode()
    require(all(t not in encoded and base64.b64encode(t) not in encoded and t.hex().encode() not in encoded for t in forbidden), 'Canary in evidence')
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open('xb') as stream:
        stream.write(encoded + b'\n')
    print(json.dumps({'status': evidence['status'], 'elapsedSeconds': evidence['elapsedSeconds'],
                      'checks': {k: v['status'] for k, v in evidence.get('checks', {}).items()}}))
    return 0 if evidence['status'] == 'PASS' else 2


if __name__ == '__main__':
    raise SystemExit(main())
