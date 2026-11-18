"""Exclusive synthetic VF1 collection and caller-pinned host-response derivation."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'spikes/vf1')]
from core_bridge import ARTIFACT_KINDS, CHECKS, LEVELS, derive, job_digest

CASE = ROOT / 'examples/mock/06-filter-pagination'
OMITTED = 'Baseline.test_api_page_and_size'


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def write_new(path, value, *, compact=False):
    data = canonical(value) if compact else (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')
    with path.open('xb') as stream:
        stream.write(data)
    return hashlib.sha256(data).hexdigest()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def wsl(*args, timeout=15):
    return subprocess.run(['wsl.exe', '-d', 'Ubuntu-24.04', '--', *args], capture_output=True,
                          text=True, encoding='utf-8', timeout=timeout)


def check(condition, message):
    if not condition:
        raise RuntimeError(message)


def stage(path, run_id, job_id):
    path.mkdir(parents=True, exist_ok=False)
    hashes = {}
    for relative in ARTIFACT_KINDS:
        target = path / 'case' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((CASE / relative).read_bytes())
        hashes['case/' + relative] = sha(target)
    target = path / 'test_worker.py'
    target.write_bytes((ROOT / 'spikes/vf1/test_worker.py').read_bytes())
    hashes['test_worker.py'] = sha(target)
    write_new(path / 'marker.json', {'kind': 'vf1-input-v1', 'runId': run_id, 'jobId': job_id, 'inputHashes': hashes})
    return hashes


def actual_run(output, staging, run_id, job_id):
    expected_hashes = stage(staging, run_id, job_id)
    linux_root = wsl('wslpath', '-a', ROOT.as_posix()).stdout.strip()
    check(linux_root.startswith('/mnt/'), 'WSL checkout path unresolved')
    unit = 'qa-s4-vf1-' + uuid.uuid4().hex + '.service'
    args = ['wsl.exe', '-d', 'Ubuntu-24.04', '-u', 'root', '--', 'systemd-run', '--unit=' + unit,
            '--wait', '--pipe', '--collect', '--property=User=phucpn', '--property=Group=phucpn',
            '--property=Delegate=yes', '--property=DelegateSubgroup=supervisor', '--property=MemoryMax=768M',
            '--property=TasksMax=256', '--property=RuntimeMaxSec=180', '/usr/bin/python3', '-I', '-S', '-B',
            linux_root + '/spikes/vf1/linux_worker.py',
            linux_root + '/' + staging.relative_to(ROOT).as_posix(), run_id, job_id]
    with (output / 'worker.stdout.json').open('xb') as out, (output / 'worker.stderr.txt').open('xb') as err:
        process = subprocess.Popen(args, stdout=out, stderr=err)
        try:
            exit_code = process.wait(timeout=200)
        except subprocess.TimeoutExpired:
            subprocess.run(['wsl.exe', '-d', 'Ubuntu-24.04', '-u', 'root', '--', 'systemctl', 'stop', unit],
                           capture_output=True, timeout=30)
            process.kill()
            process.wait(timeout=10)
            raise RuntimeError('Worker timeout; inspect exact owned unit before next effect')
    state = wsl('systemctl', 'show', unit, '--property=LoadState', '--value')
    absent = wsl('test', '!', '-e', '/sys/fs/cgroup/system.slice/' + unit)
    teardown = {'unit': unit, 'loadState': state.stdout.strip(), 'cgroupAbsent': absent.returncode == 0,
                'workerExitCode': exit_code}
    write_new(output / 'supervisor.json', teardown)
    record = json.loads((output / 'worker.stdout.json').read_bytes())
    check(exit_code == 0 and record.get('status') == 'complete', 'Worker unresolved; inspect preserved private diagnostic')
    check(teardown['loadState'] == 'not-found' and teardown['cgroupAbsent'], 'Supervisor cleanup unresolved')
    check(record['runId'] == run_id and record['jobId'] == job_id and record['inputHashes'] == expected_hashes,
          'Execution input identity mismatch')
    check(all(value is True for value in record['cleanup'].values()), 'Container cleanup unresolved')
    check(all(sha(staging / name) == value for name, value in expected_hashes.items()), 'Staged source mutated')
    return record


def staged_payloads(staging, input_hashes):
    payloads = {name:(staging / name).read_bytes() for name in input_hashes}
    check(all(hashlib.sha256(raw).hexdigest()==input_hashes[name] for name,raw in payloads.items()),
          'Staged bytes no longer match executed input pins')
    return payloads


def build_job(record, execution_sha, withheld, payloads):
    artifacts = []
    for index, (relative, kind) in enumerate(ARTIFACT_KINDS.items(), 1):
        raw = payloads['case/' + relative]
        check(hashlib.sha256(raw).hexdigest()==record['inputHashes']['case/' + relative],
              'Offered source differs from executed input pins')
        artifacts.append({'id': 'artifact-' + str(index), 'kind': kind, 'relativePath': relative,
                          'sha256': hashlib.sha256(raw).hexdigest(), 'text': raw.decode('utf-8')})
    by_path = {item['relativePath']: item for item in artifacts}
    criteria = []
    for criterion_id in LEVELS:
        row = next(line for line in artifacts[0]['text'].splitlines() if line.startswith('| ' + criterion_id + ' | '))
        criteria.append({'id': criterion_id, 'expected': row.split('|', 2)[2].removesuffix('|').strip(), 'locator': criterion_id})
    observations = []
    for index, item in enumerate(record['execution']['observations'], 1):
        if item['testId'] in withheld:
            continue
        path, level = CHECKS[item['testId']]
        trace = item['traceText'].strip()
        # Only a bounded assertion/error tail enters the private reasoning request.
        reason = None if item['outcome'] == 'pass' else (trace[-256:] or item['outcome'])
        observations.append({'id': record['runId'] + '-e' + str(index), 'testId': item['testId'],
                             'outcome': item['outcome'], 'level': level,
                             'checkArtifactId': by_path[path]['id'], 'reason': reason})
    return {'version': 'vf1-job-1.0.0', 'classification': 'synthetic-only', 'runId': record['runId'],
            'jobId': record['jobId'], 'candidateRevision': 'mock-06-head-v1', 'requirementVersion': 'mock-req-06-v1',
            'observedAt': record['finishedAt'].replace('+00:00', 'Z'), 'executionRef': record['runId'] + '-execution',
            'executionSha256': execution_sha, 'artifacts': artifacts, 'selectedCriteria': criteria,
            'policy': {'minimumLevelsByCriterion': LEVELS}, 'observations': observations}


def collect(batch):
    check(batch.parent.resolve() == (ROOT / 'docs/vf1-results').resolve(), 'Exclusive result root required')
    batch.mkdir(parents=True, exist_ok=False)
    for label in ('a', 'b'):
        output = batch / label
        output.mkdir()
        run_id = 'vf1-' + label + '-' + uuid.uuid4().hex[:16]
        job_id = 'job-' + uuid.uuid4().hex[:16]
        staging = ROOT / '.cache/s6/vf1' / batch.name / label
        record = actual_run(output, staging, run_id, job_id)
        intervention = [] if label == 'a' else [OMITTED]
        record['ingestionIntervention'] = {'withheldTestIds': intervention, 'appliedBeforeHostRequest': True}
        execution_sha = write_new(output / 'execution.json', record)
        job = build_job(record, execution_sha, intervention, staged_payloads(staging, record['inputHashes']))
        digest = write_new(output / 'host-request.json', job, compact=True)
        check(digest == job_digest(job), 'Canonical digest mismatch')
        write_new(output / 'anchors.json', {'runId': run_id, 'jobId': job_id, 'jobDigest': digest,
                                          'executionSha256': execution_sha, 'classification': 'synthetic-only'})
        print(json.dumps({'label': label, 'runId': run_id, 'counts': record['execution']['counts'], 'jobDigest': digest}), flush=True)


def validate_execution_binding(folder, label, job, anchors):
    record = json.loads((folder / 'execution.json').read_bytes())
    raw = json.loads((folder / 'worker.stdout.json').read_bytes())
    check({k:v for k,v in record.items() if k!='ingestionIntervention'}==raw,'Private execution changed from worker record')
    check(record['status']=='complete' and all(value is True for value in record['cleanup'].values()),'Execution unresolved')
    check(record['runId']==job['runId']==anchors['runId'] and record['jobId']==job['jobId']==anchors['jobId'],
          'Execution identity differs from held job anchors')
    check(sha(folder / 'execution.json')==anchors['executionSha256']==job['executionSha256'],'Execution bytes changed')
    check(sha(folder / 'host-request.json')==anchors['jobDigest']==job_digest(job),'Request bytes changed')
    withheld=[] if label=='a' else [OMITTED]
    check(record['ingestionIntervention']=={'withheldTestIds':withheld,'appliedBeforeHostRequest':True},'Ingestion policy changed')
    payloads={'case/'+item['relativePath']:item['text'].encode('utf-8') for item in job['artifacts']}
    expected=build_job(record,anchors['executionSha256'],withheld,payloads)
    check(job==expected,'Job observations/source/identity differ from pinned execution')


def write_derived_bytes(byte_outputs, *, resume_exact=False):
    for path, content in byte_outputs:
        check(not path.exists() or (resume_exact and path.read_bytes()==content),'Output already exists or differs: '+str(path))
    for path, content in byte_outputs:
        try:
            with path.open('xb') as stream:
                stream.write(content)
        except FileExistsError:
            # A concurrent file creation must receive the same check as a preexisting file.
            check(resume_exact and path.read_bytes()==content,'Concurrent output already exists or differs: '+str(path))


def derive_batch(batch, *, resume_exact=False):
    views = []
    pending = []
    for label in ('a', 'b'):
        output = batch / label
        job = json.loads((output / 'host-request.json').read_bytes())
        anchors = json.loads((output / 'anchors.json').read_bytes())
        validate_execution_binding(output,label,job,anchors)
        response = json.loads((output / 'host-response.json').read_bytes())
        try:
            result = derive(job, response, expected_job_digest=anchors['jobDigest'], report_id=job['runId'] + '-report')
        except Exception as error:
            raise RuntimeError('Derivation rejected for run ' + label) from error
        for name, value in result.items():
            pending.append((output / (name + '.json'), value))
        views.append(result['view'])
    payload = {'version': 'vf1-viewer-1.0.0', 'reports': views}
    pending.append((batch / 'viewer-data.json', payload))
    template = (ROOT / 'spikes/vf1/viewer.html').read_text(encoding='utf-8')
    data = canonical(payload).decode('utf-8').replace('<', '\\u003c').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
    byte_outputs = [(path, (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8'))
                    for path, value in pending]
    byte_outputs.append((batch / 'dashboard.html', template.replace('/*VF1_DATA*/null', data).encode('utf-8')))
    # Validate the complete batch before writing; explicit resume may reuse only byte-identical output.
    write_derived_bytes(byte_outputs,resume_exact=resume_exact)
    print(json.dumps([{'runId': v['runId'], 'criteria': [(c['criterionId'], c['status']) for c in v['criteria']]} for v in views]))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('operation', choices=('collect', 'derive'))
    parser.add_argument('batch')
    parser.add_argument('--resume-exact', action='store_true')
    args = parser.parse_args()
    check(re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}', args.batch), 'Invalid batch ID')
    batch = ROOT / 'docs/vf1-results' / args.batch
    if args.operation == 'collect':
        check(not args.resume_exact, 'Collection never resumes or overwrites execution')
        collect(batch)
    else:
        derive_batch(batch, resume_exact=args.resume_exact)
