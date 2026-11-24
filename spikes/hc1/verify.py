"""Read-only actual-run and baseline audit; writes only a fresh audit file."""
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import orchestrator as hc


def audit(batch, baseline_folder):
    checks = []
    pins = hc.read(baseline_folder / 'producer-before-r3.json')
    hc.need(pins['producerVersion'] == hc.PRODUCER, 'Wrong producer')
    original_source = baseline_folder / 'orchestrator-before-cli-fix.py'
    orchestrator_path = 'spikes/hc1/orchestrator.py'
    hc.need(hc.vf.sha(original_source) == pins['files'][orchestrator_path], 'Original producer source changed')
    before = original_source.read_bytes()
    old_line = b'print(json.dumps(result, ensure_ascii=False, allow_nan=False))'
    new_line = b'print(json.dumps(result, ensure_ascii=True, allow_nan=False))'
    hc.need(before.count(old_line) == 1 and (hc.ROOT / orchestrator_path).read_bytes() == before.replace(old_line, new_line),
            'Change exceeds compatible CLI Unicode escaping fix')
    hc.need(all(hc.vf.sha(hc.ROOT / path) == value for path, value in pins['files'].items()
                if path != orchestrator_path), 'Producer source drift')
    checks.append({'check': 'producer-byte-pins', 'count': len(pins['files']), 'status': 'PASS'})
    tickets = hc.read(batch / 'caller-tickets.json')
    invocations = {row['label']: row for row in hc.read(batch / 'native-invocations.json')['invocations']}
    for label in hc.LABELS:
        folder = batch / label
        dispatch, job = hc.held_dispatch(folder, tickets[label])
        offered = hc.read(folder / 'host-offer.json')
        hc.need(offered['request'] == job and offered['dispatch'] == dispatch and
                offered['responseContract'] == hc.response_contract(job) and
                offered['dispatchDigest'] == tickets[label], 'Offer/ticket changed')
        record = hc.read(folder / 'execution.json')
        hc.need(record['execution']['counts'] == {'total': 9, 'pass': 6, 'fail': 3, 'error': 0, 'skipped': 0}, 'Unexpected actual outcomes')
        supervisor = hc.read(folder / 'supervisor.json')
        hc.need(supervisor['workerExitCode'] == 0 and supervisor['cgroupAbsent'] is True and
                supervisor['loadState'] == 'not-found', 'Supervisor unresolved')
        hc.need(all(value is True for value in record['cleanup'].values()), 'Container unresolved')
        hc.need(len(job['observations']) == (9 if label == 'a' else 8), 'Wrong offered observation count')
        hc.need((hc.vf.OMITTED in {v['testId'] for v in job['observations']}) == (label == 'a'), 'Wrong withholding')
        hc.need(hc.read(folder / 'missing-connector.json')['state'] == 'waiting_connector', 'Missing connector mislabeled')
        accepted = folder / 'accepted'
        before = {p.name: p.read_bytes() for p in accepted.iterdir()}
        completion = hc.read(accepted / 'completion.json')
        response_name = invocations[label]['responseFile']
        hc.need(response_name == 'native-response-2.json', 'Unexpected native response selection')
        hc.need(completion['response'] == hc.read(folder / response_name), 'Native response rewritten')
        receipt = hc.complete(folder, tickets[label], completion)
        hc.need(receipt == hc.receipt(folder) and hc.state(folder, tickets[label]) == 'view_ready', 'Replay rejected')
        hc.need(before == {p.name: p.read_bytes() for p in accepted.iterdir()}, 'Replay rewrote output')
        view = hc.read(accepted / 'view.json')
        # Fresh live A chose a distinct past-end obligation: its integration floor is unfilled.
        # Preserve the actual proposal/core judgment instead of forcing historical VF1's scope.
        expected = ['verified', 'failed', 'failed', 'unverified']
        hc.need([row['status'] for row in view['criteria']] == expected, 'Unexpected derived status')
        hc.need(view['humanDecision'] == 'pending' and view['verification'] == 'failed', 'Decision changed')
        hc.need(all(e['id'].startswith(job['runId']) for e in view['evidence']), 'Sibling evidence in view')
        hc.need(view['hasUnverifiedMandatory'] and view['hasOpenMandatoryCoverage'], 'Missing gap')
        checks.append({'check': 'actual-own-run-and-exact-replay', 'label': label, 'runId': job['runId'],
                       'dispatchDigest': tickets[label], 'counts': record['execution']['counts'],
                       'statuses': expected, 'status': 'PASS'})
    baseline = hc.read(baseline_folder / 'baseline-paths.json')
    prefix_allowed = {'docs/NEXT-SESSION.md', 'docs/SESSION-HANDOFF.md', 'docs/IMPLEMENTATION-PLAN.md', 'docs/DECISION-LOG.md'}
    unchanged, prefixed = [], []
    for path, value in baseline.items():
        current = (hc.ROOT / path).read_bytes()
        if hc.vf.sha(hc.ROOT / path) == value:
            unchanged.append(path)
        else:
            hc.need(path in prefix_allowed, 'Historical path changed: ' + path)
            old = subprocess.check_output(['git', 'show', 'bef018e4cbbf1696627ec5c7ca4f455a062b9d0e:' + path], cwd=hc.ROOT)
            hc.need(current.endswith(old), 'History suffix changed: ' + path)
            prefixed.append(path)
    checks.append({'check': 'baseline-preservation', 'status': 'PASS', 'total': len(baseline),
                   'unchangedCount': len(unchanged), 'prefixOnly': prefixed})
    return {'version': 'hc1-audit-1.0.0', 'status': 'PASS', 'checks': checks}


if __name__ == '__main__':
    batch = hc.ROOT / 'docs/hc1-results' / sys.argv[1]
    baseline = hc.ROOT / 'docs/hc1-results/hc1-20261118-r1'
    result = audit(batch, baseline)
    hc.put(baseline / sys.argv[2], result)
    print({'status': result['status'], 'checks': len(result['checks'])})
