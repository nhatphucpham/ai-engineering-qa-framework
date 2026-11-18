"""Audit persisted actual runs plus deterministic negative boundary checks; no execution effects."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'spikes/vf1')]
from core_bridge import BridgeError, derive, job_digest
from run_vf1 import OMITTED, check, collect, derive_batch, sha, validate_execution_binding, write_new

BASELINE = '470bd8bf12a23e4472c907f313a9f03d9ed699d6'
CURRENT_DOCS = {'docs/IMPLEMENTATION-PLAN.md', 'docs/NEXT-SESSION.md', 'docs/SESSION-HANDOFF.md', 'docs/DECISION-LOG.md'}


def permitted_vf1_attributes(original, current):
    """Allow the user-authorized Git byte-preservation append without changing old policy."""
    import re
    if not current.startswith(original):
        return False
    suffix=current[len(original):].decode('utf-8')
    lines=[line for line in suffix.splitlines() if line]
    if not lines or lines.pop(0)!='# Preserve exact reviewed VF1 source/evidence and pre-push records.':
        return False
    flags=' -text whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol'
    for line in lines:
        if not line.endswith(flags):
            return False
        path=line[:-len(flags)]
        special=path in ('/docs/VF1-PROTOCOL.md','/docs/VF1-RESULTS.md','/docs/VF1-PUSH-REVIEW-2026-11-18.md')
        scoped=re.fullmatch(r'/(?:spikes/vf1|docs/vf1-results)/[A-Za-z0-9_./-]+',path)
        if not (special or scoped) or '..' in path.split('/') or path.endswith('/'):
            return False
    return bool(lines) and len(lines)==len(set(lines))


def load(path):
    return json.loads(path.read_bytes())


def verify(batch):
    checks = []
    jobs, responses, views = {}, {}, {}
    for label in ('a', 'b'):
        folder = batch / label
        job, anchors, record = [load(folder / name) for name in ('host-request.json', 'anchors.json', 'execution.json')]
        response = load(folder / 'host-response.json')
        validate_execution_binding(folder,label,job,anchors)
        result = derive(job, response, expected_job_digest=anchors['jobDigest'], report_id=job['runId'] + '-report')
        for key in result:
            check(result[key] == load(folder / (key + '.json')), 'Derived record mismatch ' + label + '/' + key)
        check(sha(folder / 'execution.json') == anchors['executionSha256'] == job['executionSha256'], 'Execution hash mismatch')
        check(sha(folder / 'host-request.json') == anchors['jobDigest'] == job_digest(job), 'Job hash mismatch')
        raw = load(folder / 'worker.stdout.json')
        check({k:v for k,v in record.items() if k != 'ingestionIntervention'} == raw, 'Worker observations changed')
        check(record['execution']['counts'] == {'total':9,'pass':6,'fail':3,'error':0,'skipped':0}, 'Unexpected configured observations')
        check(record['status'] == 'complete' and all(value is True for value in record['cleanup'].values()), 'Cleanup unresolved')
        supervisor = load(folder / 'supervisor.json')
        check(supervisor['loadState'] == 'not-found' and supervisor['cgroupAbsent'] and supervisor['workerExitCode'] == 0, 'Supervisor remains')
        withheld = [] if label == 'a' else [OMITTED]
        check(record['ingestionIntervention'] == {'withheldTestIds':withheld,'appliedBeforeHostRequest':True}, 'Wrong intervention')
        offered = [item for item in raw['execution']['observations'] if item['testId'] not in withheld]
        check([(i['testId'],i['outcome']) for i in offered] == [(i['testId'],i['outcome']) for i in job['observations']], 'Offered execution differs')
        check(result['view']['humanDecision'] == 'pending' and result['view']['verification'] == 'failed', 'Approval/overall semantics changed')
        for artifact in job['artifacts']:
            check(artifact['sha256'] == sha(ROOT / 'examples/mock/06-filter-pagination' / artifact['relativePath']), 'Source drift')
        jobs[label], responses[label], views[label] = job, response, result['view']
        checks.append({'id':'actual-' + label,'status':'PASS','runId':job['runId'],'counts':raw['execution']['counts']})
    check({o['id'] for o in jobs['a']['observations']}.isdisjoint({o['id'] for o in jobs['b']['observations']}), 'Cross-run evidence identity reused')
    for label, expected in [('a',['verified','failed','failed','verified']),('b',['verified','failed','failed','unverified'])]:
        check([c['status'] for c in views[label]['criteria']] == expected, 'Paired selected acceptance differs')
    check(not views['a']['hasUnverifiedMandatory'] and views['b']['hasUnverifiedMandatory'], 'Incomplete flag lost')
    checks.append({'id':'paired-verdicts-own-run','status':'PASS'})
    originals = {str(path):sha(path) for path in batch.rglob('*') if path.is_file()}
    for name, operation in [('duplicate-collection',lambda:collect(batch)),('duplicate-report',lambda:derive_batch(batch))]:
        try:
            operation()
        except (FileExistsError, RuntimeError):
            check(originals=={str(path):sha(path) for path in batch.rglob('*') if path.is_file()},'Duplicate attempt changed records')
            checks.append({'id':name,'status':'PASS','recordsUnchanged':True})
        else:
            raise RuntimeError('Duplicate operation accepted')

    def rejected(name, job, response, held=None):
        try:
            derive(job, response, expected_job_digest=held or job_digest(job), report_id=job['runId'] + '-negative')
        except BridgeError as error:
            checks.append({'id':name,'status':'PASS','rejection':error.code})
        else:
            raise RuntimeError('Negative accepted: ' + name)
    wrong = deepcopy(jobs['a']); wrong['candidateRevision']='other-revision'
    rejected('wrong-revision',wrong,responses['a'])
    wrong = deepcopy(jobs['a']); wrong['observedAt']='2026-11-18T00:00:00Z'
    rejected('wrong-held-digest',wrong,responses['a'],job_digest(jobs['a']))
    rejected('sibling-response',jobs['b'],responses['a'])
    wrong = deepcopy(responses['a']); wrong['bindings'][0]['evidenceId']='never-offered'
    rejected('nonoffered-evidence',jobs['a'],wrong)
    wrong = deepcopy(jobs['a']); wrong['artifacts'][0]['text'] += ' changed'
    rejected('source-hash-mismatch',wrong,responses['a'])
    for outcome in ('error','skipped'):
        job, response = deepcopy(jobs['a']), deepcopy(responses['a'])
        ids = {obs['id'] for obs in job['observations'] if obs['outcome']=='fail'}
        for obs in job['observations']:
            if obs['id'] in ids: obs.update(outcome=outcome,reason='Authored negative-test input; not new execution')
        for binding in response['bindings']:
            if binding['evidenceId'] in ids: binding['relation']='inconclusive'
        response['jobDigest'] = job_digest(job)
        view = derive(job,response,expected_job_digest=job_digest(job),report_id=job['runId']+'-negative')['view']
        check(all(c['status']=='unverified' for c in view['criteria'] if c['criterionId'] in ('AC-02','AC-03')), 'Error/skipped became defect or pass')
        checks.append({'id':outcome+'-not-defect','status':'PASS','classification':'authored negative input only'})

    baseline = load(batch / 'baseline-paths.json')
    preserved, prefixes, appends = 0, [], []
    for relative, expected_hash in baseline.items():
        path = ROOT / relative
        if sha(path) == expected_hash:
            preserved += 1
        else:
            original = subprocess.check_output(['git','show',BASELINE+':'+relative],cwd=ROOT)
            import hashlib
            check(hashlib.sha256(original).hexdigest()==expected_hash,'Baseline bytes differ')
            if relative=='.gitattributes':
                check(permitted_vf1_attributes(original,path.read_bytes()),'Historical attributes changed outside scoped VF1 append')
                appends.append(relative)
            else:
                check(relative in CURRENT_DOCS and path.read_bytes().endswith(original),'Historical path or document suffix changed: '+relative)
                prefixes.append(relative)
    checks.append({'id':'historical-preservation','status':'PASS','unchangedPaths':preserved,'prefixOnlyDocs':prefixes,
                   'appendOnlyBytePolicy':appends,'baselinePaths':len(baseline)})
    return {'version':'vf1-audit-1.0.0','status':'PASS','checks':checks}


if __name__ == '__main__':
    batch = ROOT / 'docs/vf1-results' / sys.argv[1]
    check(batch.parent.resolve()==(ROOT/'docs/vf1-results').resolve(),'Invalid batch path')
    import re
    check(re.fullmatch(r'[a-z0-9-]+\.json',sys.argv[2]),'Invalid audit filename')
    result = verify(batch)
    write_new(batch / sys.argv[2],result)
    print(json.dumps(result))
