"""HC1 trusted-local orchestration experiment; native host invocation stays external."""

import argparse
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'spikes/vf1')]
import run_vf1 as vf
from core_bridge import derive, validate_job

DISPATCH = 'hc1-dispatch-1.0.0'
COMPLETION = 'hc1-completion-1.0.0'
PRODUCER = 'hc1-orchestrator-1.0.1'
LABELS = ('a', 'b')


class Rejected(ValueError):
    pass


def need(condition, message):
    if not condition:
        raise Rejected(message)


def encode(value):
    return vf.canonical(value)


def digest(value):
    return hashlib.sha256(encode(value)).hexdigest()


def read(path):
    # Reject duplicate keys and nonfinite JSON rather than silently normalizing them.
    def pairs(items):
        result = {}
        for key, value in items:
            need(key not in result, 'Duplicate JSON key')
            result[key] = value
        return result
    def constant(_):
        raise Rejected('Nonfinite JSON')
    return json.loads(path.read_bytes(), object_pairs_hook=pairs, parse_constant=constant)


def put(path, value):
    with path.open('xb') as stream:
        stream.write(encode(value))
        stream.flush()


def utc():
    return datetime.now(timezone.utc)


def response_contract(job):
    assessment = read(ROOT / 'schemas/qa-assessment-v2.schema.json')
    properties = {key: deepcopy(assessment['properties'][key])
                  for key in ('risk', 'criteria', 'evidenceReviews', 'bindings')}
    properties.update({'version': {'const': 'vf1-host-response-1.0.0'},
                       'runId': {'const': job['runId']}, 'jobId': {'const': job['jobId']},
                       'jobDigest': {'const': digest(job)}})
    schema = {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'type': 'object',
              'properties': properties, 'required': list(properties), 'additionalProperties': False,
              '$defs': deepcopy(assessment['$defs'])}
    return {'version': 'hc1-response-contract-1.0.0', 'schema': schema,
            'instructions': (ROOT / 'spikes/hc1/HOST-INSTRUCTIONS.md').read_text(encoding='utf-8')}


def stamp(now):
    return now.isoformat().replace('+00:00', 'Z')


def expired(dispatch, now):
    return now >= datetime.fromisoformat(dispatch['deadline'].replace('Z', '+00:00'))


@contextmanager
def locked(folder):
    lock = folder / '.mutation-lock'
    try:
        lock.mkdir()
    except FileExistsError as exc:
        raise Rejected('Concurrent mutation or abandoned lock; inspect before recovery') from exc
    try:
        yield
    finally:
        lock.rmdir()


def bound(folder):
    job, anchors = read(folder / 'host-request.json'), read(folder / 'anchors.json')
    label = read(folder / 'hc1-run.json')['label']
    need(label in LABELS, 'Unknown run label')
    vf.validate_execution_binding(folder, label, job, anchors)
    validate_job(job, anchors['jobDigest'])
    return job, anchors


def held_dispatch(folder, held):
    need(isinstance(held, str) and re.fullmatch('[0-9a-f]{64}', held), 'Invalid caller ticket')
    dispatch = read(folder / 'dispatch.json')
    need(digest(dispatch) == held, 'Caller ticket mismatch')
    need(dispatch['version'] == DISPATCH, 'Unsupported dispatch version')
    job, anchors = bound(folder)
    expected = {key: job[key] for key in ('runId', 'jobId', 'candidateRevision', 'requirementVersion')}
    expected.update(jobDigest=anchors['jobDigest'], executionSha256=anchors['executionSha256'])
    expected['responseContractDigest'] = digest(response_contract(job))
    need(all(dispatch[key] == value for key, value in expected.items()), 'Dispatch no longer binds executed input')
    return dispatch, job


def collect(batch):
    """Fixed executor only; never run commands from a request/proposal."""
    need(batch.parent.resolve() == (ROOT / 'docs/hc1-results').resolve(), 'Invalid result root')
    batch.mkdir(exist_ok=False)
    for label in LABELS:
        folder = batch / label
        folder.mkdir()
        run_id, job_id = 'hc1-' + label + '-' + uuid.uuid4().hex[:16], 'job-' + uuid.uuid4().hex[:16]
        # Reuse the worker's existing strict input allowlist, in a fresh HC1 namespace.
        staging = ROOT / '.cache/s6/vf1' / batch.name / label
        record = vf.actual_run(folder, staging, run_id, job_id)
        withheld = [] if label == 'a' else [vf.OMITTED]
        record['ingestionIntervention'] = {'withheldTestIds': withheld, 'appliedBeforeHostRequest': True}
        execution_hash = vf.write_new(folder / 'execution.json', record)
        job = vf.build_job(record, execution_hash, withheld, vf.staged_payloads(staging, record['inputHashes']))
        request_hash = vf.write_new(folder / 'host-request.json', job, compact=True)
        put(folder / 'anchors.json', {'runId': run_id, 'jobId': job_id, 'jobDigest': request_hash,
                                     'executionSha256': execution_hash, 'classification': 'synthetic-only'})
        put(folder / 'hc1-run.json', {'version': 'hc1-run-1.0.0', 'label': label})
        print(json.dumps({'label': label, 'runId': run_id, 'counts': record['execution']['counts']}), flush=True)


def offer(folder, transport=None, *, seconds=1800, now=None, _reserve_invocation=False):
    """Issue once, never invoke. Caller retains returned digest outside the response."""
    now = now or utc()
    with locked(folder):
        job, anchors = bound(folder)
        if transport is None:
            need(not (folder / 'dispatch.json').exists(), 'Already dispatched')
            return {'state': 'waiting_connector', 'runId': job['runId']}
        need(isinstance(transport, dict) and set(transport) == {'kind', 'agentTask', 'model', 'effort'},
             'Invalid caller transport metadata')
        need(transport['kind'] in ('session-mediated', 'authored-conformance'), 'Unsupported transport')
        need(all(isinstance(v, str) and 0 < len(v) <= 160 for v in transport.values()), 'Invalid transport values')
        need(type(seconds) is int and 1 <= seconds <= 3600, 'Deadline budget outside 1..3600 seconds')
        reserved = False
        if (folder / 'dispatch.json').exists():
            dispatch = read(folder / 'dispatch.json')
            need(dispatch['transport'] == transport, 'Dispatch already owned by another transport')
            ticket = digest(dispatch)
            held_dispatch(folder, ticket)
        else:
            dispatch = {'version': DISPATCH, 'attemptId': 'attempt-' + uuid.uuid4().hex,
                        **{key: job[key] for key in ('runId', 'jobId', 'candidateRevision', 'requirementVersion')},
                        'jobDigest': anchors['jobDigest'], 'executionSha256': anchors['executionSha256'],
                        'responseContractDigest': digest(response_contract(job)),
                        'issuedAt': stamp(now), 'deadline': stamp(now + timedelta(seconds=seconds)),
                        'transport': deepcopy(transport)}
            put(folder / 'dispatch.json', dispatch)
            ticket = digest(dispatch)
            if _reserve_invocation:
                put(folder / 'invocation.json', {'version': 'hc1-invocation-1.0.0', 'dispatchDigest': ticket})
                reserved = True
        result = {'state': state(folder, ticket, now=now), 'dispatchDigest': ticket,
                  'dispatch': dispatch, 'request': job, 'responseContract': response_contract(job)}
        if _reserve_invocation:
            result['invocationReserved'] = reserved
        return result


def publication(dispatch, job, completion):
    """Deterministic projection; same producer version is required for exact replay."""
    held = digest(dispatch)
    need(isinstance(completion, dict) and set(completion) == {'version', 'dispatchDigest', 'response'}
         and completion['version'] == COMPLETION and completion['dispatchDigest'] == held, 'Stored completion changed')
    result = derive(job, completion['response'], expected_job_digest=dispatch['jobDigest'],
                    report_id=job['runId'] + '-report')
    payload = {'version': 'vf1-viewer-1.0.0', 'reports': [result['view']]}
    template = (ROOT / 'spikes/vf1/viewer.html').read_text(encoding='utf-8')
    template = template.replace('Báo cáo QA từ hai lần chạy synthetic', 'Báo cáo QA của lần chạy synthetic này')
    template = template.replace('báo cáo từ hai lần chạy mới', 'báo cáo từ lần chạy mới này')
    # VF1's two-run labels cannot be reused for a one-run projection (especially B).
    template = template.replace("index===0?'A · Đủ gói evidence':'B · Thiếu evidence phân trang'", "'Lần chạy · '+item.runId")
    escaped = encode(payload).decode('utf-8').replace('<', '\\u003c').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
    dashboard = ('<!doctype html><html lang="vi"><head><meta charset="utf-8">'
                 '<meta name="viewport" content="width=device-width, initial-scale=1">'
                 '<title>HC1 — QA synthetic</title><style>body{margin:0}</style></head><body>'
                 + template.replace('/*VF1_DATA*/null', escaped) + '</body></html>')
    outputs = {name + '.json': encode(value) for name, value in result.items()}
    outputs.update({'completion.json': encode(completion), 'viewer-data.json': encode(payload),
                    'dashboard.html': dashboard.encode('utf-8')})
    record = {'version': 'hc1-receipt-1.0.0', 'producerVersion': PRODUCER,
              'dispatchDigest': held, 'completionDigest': digest(completion),
              'runId': job['runId'], 'jobDigest': dispatch['jobDigest'], 'state': 'view_ready',
              'humanDecision': result['view']['humanDecision'],
              'templateSha256': vf.sha(ROOT / 'spikes/vf1/viewer.html'),
              'files': {name: hashlib.sha256(raw).hexdigest() for name, raw in outputs.items()}}
    return outputs, record


def receipt(folder):
    accepted = folder / 'accepted'
    dispatch, job = held_dispatch(folder, digest(read(folder / 'dispatch.json')))
    outputs, expected = publication(dispatch, job, read(accepted / 'completion.json'))
    files = {p.name for p in accepted.iterdir() if p.is_file()}
    need(files == set(outputs) | {'receipt.json'} and len(list(accepted.iterdir())) == len(files),
         'Accepted output inventory changed')
    need(all((accepted / name).read_bytes() == raw for name, raw in outputs.items()), 'Accepted output bytes changed')
    # Receipt metadata and keys are derived again, never trusted from its self-hash inventory.
    need((accepted / 'receipt.json').read_bytes() == encode(expected), 'Accepted receipt bytes changed or producer incompatible')
    return expected


def state(folder, held, *, now=None):
    dispatch, _ = held_dispatch(folder, held)
    need(not ((folder / 'accepted').exists() and (folder / 'cancel.json').exists()), 'Conflicting terminal records')
    if (folder / 'accepted').exists():
        need(receipt(folder)['dispatchDigest'] == held, 'Accepted ticket mismatch')
        return 'view_ready'
    if (folder / 'cancel.json').exists():
        need(read(folder / 'cancel.json')['dispatchDigest'] == held, 'Cancel ticket mismatch')
        return 'cancelled'
    if expired(dispatch, now or utc()):
        return 'expired'
    return 'waiting_response'


def cancel(folder, held, *, now=None):
    with locked(folder):
        held_dispatch(folder, held)
        current = state(folder, held, now=now)
        need(current != 'view_ready', 'Accepted result cannot be cancelled')
        if current != 'cancelled':
            put(folder / 'cancel.json', {'version': 'hc1-cancel-1.0.0', 'dispatchDigest': held,
                                       'at': stamp(now or utc())})
        return {'state': 'cancelled'}


def complete(folder, held, completion, *, now=None):
    with locked(folder):
        dispatch, job = held_dispatch(folder, held)
        need(isinstance(completion, dict) and set(completion) == {'version', 'dispatchDigest', 'response'},
             'Unexpected completion fields')
        need(completion['version'] == COMPLETION, 'Unsupported completion version')
        need(completion['dispatchDigest'] == held, 'Completion ticket mismatch')
        completion_hash = digest(completion)
        current = state(folder, held, now=now)
        if current == 'view_ready':
            existing = receipt(folder)
            need(existing['completionDigest'] == completion_hash, 'Conflicting duplicate completion')
            return existing
        need(current == 'waiting_response', 'Completion fenced: ' + current)
        submissions = folder / 'submissions'
        submissions.mkdir(exist_ok=True)
        submission = submissions / (completion_hash + '.json')
        if submission.exists():
            need(submission.read_bytes() == encode(completion), 'Submission bytes changed')
        else:
            put(submission, completion)
        # A malformed proposal never publishes a partial report or changes collector outcomes.
        outputs, record = publication(dispatch, job, completion)
        temporary = folder / ('.publish-' + uuid.uuid4().hex)
        temporary.mkdir()
        try:
            for name, raw in outputs.items():
                with (temporary / name).open('xb') as stream:
                    stream.write(raw)
            put(temporary / 'receipt.json', record)
            # Recheck deadline immediately before publishing, not just before core work.
            need(not expired(dispatch, now or utc()), 'Completion expired before publication')
            need(not (folder / 'accepted').exists(), 'Accepted destination already exists')
            temporary.rename(folder / 'accepted')
        finally:
            if temporary.exists():
                shutil.rmtree(temporary)
        return receipt(folder)


def drive(folder, transport, connector=None, *, seconds=1800):
    """Callable transport seam. Exception/uncertainty leaves dispatch waiting; never retry."""
    if connector is None:
        return offer(folder)
    # Only the caller that creates dispatch may reserve invocation, in the same critical section.
    # Existing dispatch without a marker can be a crash/manual native invocation: never replay it.
    issued = offer(folder, transport, seconds=seconds, _reserve_invocation=True)
    held = issued['dispatchDigest']
    if not issued['invocationReserved']:
        return {'state': issued['state'], 'dispatchDigest': held, 'reason': 'dispatch_already_issued'}
    need(state(folder, held) == 'waiting_response', 'Attempt no longer waiting')
    # Callable is trusted host integration, never obtained from artifact/model command text.
    response = connector(deepcopy(issued))
    return complete(folder, held, {'version': COMPLETION, 'dispatchDigest': held, 'response': response})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('operation', choices=('collect', 'offer', 'complete', 'cancel', 'status'))
    parser.add_argument('batch')
    parser.add_argument('--label', choices=LABELS)
    parser.add_argument('--ticket')
    parser.add_argument('--response', type=Path)
    parser.add_argument('--agent-task')
    parser.add_argument('--model', default='gpt-6.2-astra')
    parser.add_argument('--effort', default='high')
    args = parser.parse_args()
    need(re.fullmatch('[a-z0-9][a-z0-9-]{0,63}', args.batch), 'Invalid batch ID')
    batch = ROOT / 'docs/hc1-results' / args.batch
    if args.operation == 'collect':
        collect(batch)
        return
    need(args.label is not None, 'Run label required')
    folder = batch / args.label
    if args.operation == 'offer':
        transport = None if args.agent_task is None else {'kind': 'session-mediated', 'agentTask': args.agent_task,
                                                        'model': args.model, 'effort': args.effort}
        result = offer(folder, transport, seconds=3600)
    elif args.operation == 'complete':
        need(args.response is not None, 'Response path required')
        result = complete(folder, args.ticket, {'version': COMPLETION, 'dispatchDigest': args.ticket,
                                              'response': read(args.response)})
    elif args.operation == 'cancel':
        result = cancel(folder, args.ticket)
    else:
        result = {'state': state(folder, args.ticket)}
    print(json.dumps(result, ensure_ascii=True, allow_nan=False))


if __name__ == '__main__':
    main()
