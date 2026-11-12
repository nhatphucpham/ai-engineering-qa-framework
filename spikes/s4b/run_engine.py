"""Actual controlled rootless containers under an authorized transient delegate."""
from pathlib import Path
import contextlib
from datetime import datetime, timezone
import hashlib
import io
import json
import os
import re
import socket
import subprocess
import sys
import time
import traceback

from engine import RootlessEngine

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / '.cache/s6/s4-b'


def require(value, message):
    if not value:
        raise AssertionError(message)


def values(path):
    return {key: int(value) for key, value in (line.split() for line in path.read_text().splitlines())}


def exec_container(engine, container, script, timeout=10):
    require(container in engine.owned, 'Container scope mismatch')
    return engine.command(['exec', container, '/bin/sh', '-c', script], check=False, timeout=timeout)


def validate_network(links, ipv4, ipv6):
    require(all(result.returncode == 0 for result in (links, ipv4, ipv6)), 'Network inspection command failed')
    names = []
    for line in links.stdout.splitlines():
        if line.strip():
            match = re.match(r'^\s*\d+:\s+([^:]+):', line)
            require(match is not None, 'Unknown interface output')
            names.append(match.group(1))
    require(names == ['lo'], 'Network namespace has non-loopback interface')
    for line in (ipv4.stdout + '\n' + ipv6.stdout).splitlines():
        words = line.split()
        require(not any(word in ('default', '0.0.0.0/0', '::/0') for word in words), 'Default route observed')
    return {'interfaces': names, 'ipv4RouteLines': len(ipv4.stdout.splitlines()), 'ipv6RouteLines': len(ipv6.stdout.splitlines())}


def pid_state(pid):
    try:
        fields = Path('/proc/' + str(pid) + '/stat').read_text().rsplit(')', 1)[1].split()
        return {'state': fields[0], 'startTime': fields[19]}
    except FileNotFoundError:
        return None


def experiment(evidence):
    engine = RootlessEngine()
    checks = evidence['checks'] = {}
    evidence['privateEngineCache'] = str(engine.base)
    try:
        evidence['engine'] = {'podmanVersion': engine.info['version']['Version'],
                              'rootless': engine.info['host']['security']['rootless'],
                              'hostUid': os.getuid(), 'cgroupManager': engine.info['host']['cgroupManager'],
                              'cgroupVersion': engine.info['host']['cgroupVersion'],
                              'delegatedParent': str(engine.parent), 'storageDriver': 'vfs'}
        evidence['image'] = engine.build_image()
        container = engine.launch('sleep 60')
        info = engine.inspect(container); group = engine.cgroup(container)
        identity = exec_container(engine, container, 'id -u; cat /proc/self/status | grep -E "^(CapEff|NoNewPrivs):"')
        require(identity.returncode == 0 and identity.stdout.splitlines()[0] == '1000', 'Container not nonroot')
        require('CapEff:\t0000000000000000' in identity.stdout and 'NoNewPrivs:\t1' in identity.stdout, 'Privilege controls not active')
        require(not info['HostConfig']['Privileged'] and info['HostConfig']['ReadonlyRootfs'], 'Container privileged or writable root')
        checks['E01'] = {'status': 'PASS', 'hostRootlessUid': 1000, 'containerUid': 1000,
                         'zeroEffectiveCapabilities': True, 'noNewPrivsObserved': True,
                         'containerCgroupUnderDelegate': str(group), 'pinnedImageId': engine.image}

        marker = b'synthetic fixture for narrow mount\n'
        (engine.base / 'input/fixture').write_bytes(marker)
        readonly = exec_container(engine, container, 'touch /rootfs-denied >/dev/null 2>&1; r=$?; touch /input/denied >/dev/null 2>&1; i=$?; cat /input/fixture > /output/observed; printf "%s %s\\n" "$r" "$i"')
        require(readonly.returncode == 0 and all(int(x) != 0 for x in readonly.stdout.split()), 'Rootfs/input writable')
        mounts = [m for m in info.get('Mounts', []) if m.get('Type') == 'bind']
        require({m['Destination'] for m in mounts} == {'/input', '/output'}, 'Unexpected host bind mount')
        require(all(Path(m['Source']).is_relative_to(engine.base) for m in mounts), 'Broad host bind mount')
        sys.path.insert(0, str(ROOT / 'spikes/s4'))
        from collector import PrivateCollector
        fd = os.open(engine.base / 'output', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        collector = None
        try:
            stat = os.fstat(fd)
            collector = PrivateCollector(fd, (stat.st_dev, stat.st_ino),
                                         {'projectId': 'syntheticA', 'runId': 'containerA', 'assignmentId': 'fixtureA', 'attempt': 1, 'fence': 1})
            blob = collector.collect_private('observed')
            require(blob.private_bytes() == marker and blob.manifest['ordinaryRelease'] == 'DENIED', 'Private collector mount roundtrip failed')
        finally:
            if collector is not None:
                collector.close()
            os.close(fd)
        checks['E02'] = {'status': 'PASS', 'rootfs_and_input_write_denied': True,
                         'only_marked_fixture_binds': True, 'actual_output_private_collector_roundtrip': True,
                         'ordinary_raw_release': 'DENIED; no sanitizer/authenticated bridge'}

        listener = socket.socket(); listener.bind(('127.0.0.1', 0)); listener.listen(1); listener.settimeout(.2)
        port = listener.getsockname()[1]
        try:
            topology = validate_network(exec_container(engine, container, 'ip -o link'),
                                        exec_container(engine, container, 'ip -4 route show'),
                                        exec_container(engine, container, 'ip -6 route show'))
            network_pid = engine.inspect(container)['State']['Pid']
            require(os.readlink('/proc/' + str(network_pid) + '/ns/net') != os.readlink('/proc/self/ns/net'),
                    'Container shares host network namespace')
            network = exec_container(engine, container, 'wget -T 1 -q -O /tmp/network-result http://127.0.0.1:' + str(port), timeout=5)
            require(network.returncode != 0, 'Container request to synthetic sink unexpectedly succeeded')
            try:
                conn, _ = listener.accept(); conn.close()
            except socket.timeout:
                pass
            else:
                raise AssertionError('Container reached synthetic host sink')
        finally:
            listener.close()
        checks['E03'] = {'status': 'PASS', 'loopback_only_no_default_route': True, 'observedTopology': topology,
                         'networkNamespaceDifferentFromHost': True,
                         'actual_container_request_denied_host_sink_received_zero_connections': True,
                         'networkProofScope': 'isolated namespace/topology and one controlled local sink; not every possible egress',
                         'external_provider_calls': 'NOT RUN'}

        limits = {'memoryMax': (group / 'memory.max').read_text().strip(),
                  'pidsMax': (group / 'pids.max').read_text().strip(), 'cpuMax': (group / 'cpu.max').read_text().strip()}
        require(limits['memoryMax'] == str(64 * 1048576) and limits['pidsMax'] == '32'
                and limits['cpuMax'] == '50000 100000', 'Cgroup limits differ from requested caps')
        cpu_before = values(group / 'cpu.stat')
        cpu = exec_container(engine, container, 'awk \'BEGIN { end=systime()+2; while(systime()<end) x++ }\'', timeout=8)
        cpu_after = values(group / 'cpu.stat')
        require(cpu.returncode == 0 and cpu_after['nr_throttled'] > cpu_before['nr_throttled']
                and cpu_after['throttled_usec'] > cpu_before['throttled_usec'], 'CPU throttling not observed')
        pids_before = values(group / 'pids.events')
        pid_pressure = exec_container(engine, container, 'i=0; while [ "$i" -lt 48 ]; do sleep 2 & i=$((i+1)); done; wait', timeout=10)
        pids_after = values(group / 'pids.events')
        require(pids_after['max'] > pids_before['max'], 'PID enforcement event not observed')
        # Free PID-saturated container before the next bounded memory probe.
        engine.command(['stop', '--time=1', container])
        mem_container = engine.launch('sleep 60', memory='32m', pids=32)
        memory_group = engine.cgroup(mem_container)
        require((memory_group / 'memory.max').read_text().strip() == str(32 * 1048576), 'Memory cap not verified before pressure')
        memory_before = values(memory_group / 'memory.events')
        memory = exec_container(engine, mem_container, 'awk \'BEGIN { for(i=0;i<1000000;i++) a[i]=sprintf("%01024d",i) }\'', timeout=8)
        memory_after = values(memory_group / 'memory.events')
        require(memory.returncode != 0 and memory_after['oom_kill'] > memory_before['oom_kill'], 'Capped OOM kill not observed')
        checks['E04'] = {'status': 'PASS', 'actualCgroupLimits': limits,
                         'cpuNrThrottledDelta': cpu_after['nr_throttled'] - cpu_before['nr_throttled'],
                         'cpuThrottledUsecDelta': cpu_after['throttled_usec'] - cpu_before['throttled_usec'],
                         'pidsMaxEventsDelta': pids_after['max'] - pids_before['max'],
                         'memoryOomKillDelta': memory_after['oom_kill'] - memory_before['oom_kill'],
                         'memoryPressureCapBytes': 32 * 1048576, 'fixtureOnlyNoProductionSLA': True}

        long = engine.launch('sleep 60 & sleep 60 & wait')
        long_group = engine.cgroup(long)
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            pids = [int(x) for x in (long_group / 'cgroup.procs').read_text().split()]
            if len(pids) >= 3:
                break
            time.sleep(.01)
        require(len(pids) >= 3, 'Descendant workload not observed')
        before = {pid: pid_state(pid) for pid in pids}
        begin = time.monotonic(); engine.command(['stop', '--time=1', long], timeout=12)
        elapsed = time.monotonic() - begin
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            after = {pid: pid_state(pid) for pid in pids}
            live = [pid for pid, value in after.items() if value is not None and value['state'] != 'Z'
                    and before[pid] is not None and value['startTime'] == before[pid]['startTime']]
            if not live:
                break
            time.sleep(.02)
        stopped = engine.inspect(long)['State']
        require(not stopped['Running'] and stopped['Pid'] == 0 and not live and elapsed < 10,
                'Stop/descendant cleanup unconfirmed')
        empty = not long_group.exists() or not (long_group / 'cgroup.procs').read_text().strip()
        require(empty, 'Stopped container cgroup still populated')
        checks['E05'] = {'status': 'PASS', 'observedProcessCount': len(pids), 'stopSeconds': elapsed,
                         'containerStoppedPidZero': True, 'originalProcessesNotLive': True, 'cgroupEmptyOrRemoved': True,
                         'authenticated_cancel_revoke_pipeline': 'NOT RUN'}

        repeat = engine.launch('id -u; sleep 2')
        require(engine.inspect(repeat)['State']['Running'], 'Fresh repeated container not running')
        require(repeat not in (container, mem_container, long), 'Container identity reused')
        checks['E06'] = {'status': 'PASS', 'freshContainerIdentityAndExactPinnedImage': True,
                         'engine_restart_crash_recovery': 'NOT RUN', 'cleanupRecordedSeparately': True}
    finally:
        evidence['ownedCleanup'] = engine.cleanup()


def inputs():
    paths = [p for p in (ROOT / 'spikes/s4b').rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    paths += [ROOT / 'docs/S4-B-PROTOCOL.md', ROOT / 'spikes/s4/collector.py']
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


def main():
    if len(sys.argv) != 3 or not re.fullmatch('[a-f0-9]{40}', sys.argv[2]):
        raise SystemExit('Use new docs/s4b-results/<id>.json and caller-held baseline')
    dest = (ROOT / sys.argv[1]).resolve()
    if dest.parent != (ROOT / 'docs/s4b-results').resolve() or dest.exists() or dest.suffix != '.json':
        raise SystemExit('Use a fresh S4-B evidence file')
    CACHE.mkdir(parents=True, exist_ok=True)
    evidence = {'evidenceVersion': 's4-b-1.0.0', 'classification': 'synthetic-only', 'baseline': sys.argv[2],
                'startedAt': datetime.now(timezone.utc).isoformat(), 'inputsBefore': inputs(), 'status': 'RUNNING',
                'limits': ['Authorized WSL system setup, actual rootless synthetic containers in transient delegate only',
                           'No production stack choice, authenticated IAP-B/worker/cancel-revoke/broker/end-to-end readiness',
                           'Private collector roundtrip only, no sanitized ordinary content/export or encrypted quarantine']}
    begin = time.monotonic(); stdout = io.StringIO(); stderr = io.StringIO()
    try:
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            experiment(evidence)
        evidence['inputsAfter'] = inputs(); require(evidence['inputsBefore'] == evidence['inputsAfter'], 'Source changed')
        evidence['status'] = 'PASS'
    except Exception as error:
        evidence['status'] = 'ERROR'; evidence['errorType'] = type(error).__name__
        (CACHE / (dest.stem + '-error.log')).write_text(traceback.format_exc(), encoding='utf-8')
    evidence['elapsedSeconds'] = time.monotonic() - begin
    evidence['finishedAt'] = datetime.now(timezone.utc).isoformat()
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open('x', encoding='utf-8') as stream:
        json.dump(evidence, stream, indent=2); stream.write('\n')
    print(json.dumps({'status': evidence['status'], 'elapsedSeconds': evidence['elapsedSeconds'],
                      'checks': {key: value['status'] for key, value in evidence.get('checks', {}).items()}}))
    return 0 if evidence['status'] == 'PASS' else 2


if __name__ == '__main__':
    raise SystemExit(main())
