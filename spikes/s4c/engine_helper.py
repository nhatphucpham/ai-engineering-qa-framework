"""Owned local pipe helper. No credentials, arbitrary commands or public cleanup API."""
from pathlib import Path
import json
import re
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'spikes/s4b'))
from engine import RootlessEngine
from run_engine import pid_state, require


def main():
    engine = RootlessEngine(); generation = uuid.uuid4().hex; jobs = {}; launches = 0
    try:
        image = engine.build_image()
        print(json.dumps({'ready': True, 'generation': generation, 'image': image, 'hostUid': 1000,
                          'delegatedParent': str(engine.parent), 'privateCache': str(engine.base)}), flush=True)
        for line in sys.stdin:
            try:
                command = json.loads(line)
                require(type(command) is dict and set(command) == {'op', 'job'}, 'Unknown helper fields')
                job = command['job']; op = command['op']
                require(type(job) is str and re.fullmatch('[a-f0-9]{32}', job), 'Invalid job')
                if op == 'register':
                    require(job not in jobs, 'Duplicate registration')
                    jobs[job] = {'attempted': False, 'container': None, 'cleaned': False}
                    result = {'registered': True}
                else:
                    require(job in jobs, 'Unknown job'); item = jobs[job]
                    if op == 'registered':
                        require(not item['cleaned'], 'Already cleaned')
                        result = {'registered': True, 'launchCount': launches,
                                  'privateContainerCount': len(json.loads(engine.command(['ps', '--all', '--format=json']).stdout)),
                                  'containerRunningObserved': (engine.inspect(item['container'])['State']['Running']
                                                               if item['container'] is not None else None)}
                    elif op == 'launch':
                        require(not item['attempted'] and not item['cleaned'], 'Duplicate launch')
                        item['attempted'] = True
                        container = engine.launch('sleep 120 & sleep 120 & wait')
                        item['container'] = container; launches += 1
                        group = engine.cgroup(container); item['group'] = group
                        deadline = time.monotonic() + 3
                        while time.monotonic() < deadline:
                            pids = [int(x) for x in (group / 'cgroup.procs').read_text().split()]
                            if len(pids) >= 3:
                                break
                            time.sleep(.01)
                        require(len(pids) >= 3, 'Descendants missing')
                        item['pids'] = {pid: pid_state(pid) for pid in pids}
                        require(all(item['pids'].values()), 'Process identity missing')
                        result = {'containerId': container, 'processCount': len(pids), 'launchCount': launches,
                                  'imageId': engine.image, 'hostUid': 1000, 'containerCgroup': str(group)}
                    elif op == 'cleanup':
                        require(not item['cleaned'], 'Cleanup replay')
                        container = item['container']; begin = time.monotonic()
                        if container is not None:
                            require('pids' in item, 'Incomplete launch observation')
                            engine.command(['stop', '--time=1', container], timeout=12)
                            stopped = engine.inspect(container)['State']
                            require(not stopped['Running'] and stopped['Pid'] == 0, 'Container not stopped')
                            for pid, original in item['pids'].items():
                                now = pid_state(pid)
                                require(now is None or now['state'] == 'Z' or now['startTime'] != original['startTime'], 'Live original PID')
                            group = item['group']
                            require(not group.exists() or not (group / 'cgroup.procs').read_text().strip(), 'Live cgroup')
                            engine.command(['rm', container])
                            require(engine.command(['inspect', container], check=False).returncode != 0, 'Container remains')
                            engine.owned.remove(container)
                        else:
                            require(not item['attempted'], 'Ambiguous launch cannot prove cleanup')
                        item['cleaned'] = True
                        result = {'jobId': job, 'generation': generation, 'originalProcessesNotLive': True,
                                  'cgroupEmptyOrRemoved': True, 'containerRemoved': True,
                                  'neverDispatched': container is None, 'cleanupSeconds': time.monotonic() - begin,
                                  'launchCount': launches}
                    else:
                        raise ValueError('Unknown helper route')
                print(json.dumps({'ok': True, 'result': result}), flush=True)
            except Exception:
                print('{"ok":false,"code":"E_HELPER"}', flush=True)
    finally:
        engine.cleanup()


if __name__ == '__main__':
    main()
