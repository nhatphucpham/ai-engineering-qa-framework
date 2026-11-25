"""Read-only staged-byte audit; optional exclusive snapshot capture before commit."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
NEW = {'docs/RC1-PUSH-REVIEW-2026-11-25.md'} | {
    'docs/rc1-push-20261125/' + name for name in ('baseline.json', 'checks.json', 'audit.py', 'snapshot.json', 'snapshot-r2.json', 'review.json')}
RECURSIVE = {'docs/rc1-push-20261125/snapshot-r2.json', 'docs/rc1-push-20261125/review.json'}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def read(name):
    return json.loads((ROOT / name).read_text(encoding='utf-8'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', action='store_true')
    args = parser.parse_args()
    capture = HERE / 'snapshot-r2.json'
    if args.capture and capture.exists():
        parser.error('snapshot exists; never overwrite retained evidence')
    baseline = read('docs/rc1-push-20261125/baseline.json')
    failures = []
    def check(condition, message):
        if not condition:
            failures.append(message)
    check(git('branch', '--show-current').decode().strip() == 'master', 'branch')
    check(git('rev-parse', 'HEAD').decode().strip() == baseline['head'], 'baseline HEAD before commit')
    check(git('ls-remote', 'origin', 'refs/heads/master').decode().split()[0] == baseline['head'], 'remote before push')
    for name, pin in baseline['files'].items():
        path = ROOT / name
        if not path.is_file():
            failures.append('missing original ' + name)
            continue
        raw = path.read_bytes()
        if name == '.gitattributes':
            length = pin['bytes']
            check(sha(raw[:length]) == pin['sha256'], 'original reviewed attributes prefix')
            added = [line for line in raw[length:].decode().splitlines() if line and not line.startswith('#')]
            expected = {'/' + p + ' -text whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol' for p in NEW}
            check(set(added) == expected and len(added) == len(expected), 'only exact new push attributes')
        else:
            check(len(raw) == pin['bytes'] and sha(raw) == pin['sha256'], 'preserved raw original ' + name)
    current = set(filter(None, git('ls-files', '-z').decode().split('\0'))) | set(filter(None,
                  git('ls-files', '--others', '--exclude-standard', '-z').decode().split('\0')))
    check(current - set(baseline['files']) <= NEW, 'new delivery file scope')
    staged = set(filter(None, git('diff', '--cached', '--name-only', '-z').decode().split('\0')))
    expected_staged = set(baseline['changedPaths']) | NEW
    # snapshot is captured after the substantive staged payload; admin files follow.
    check(staged - RECURSIVE == expected_staged - RECURSIVE, 'exact substantive staged set')
    if not args.capture:
        check(staged == expected_staged, 'complete final staged set')
    files = {}
    secret_hits = []
    for name in sorted(staged):
        check(not name.startswith('.cache/') and not re.search(r'(^|/)(?:\.env|[^/]+\.(?:pem|key))$', name), 'private staged path ' + name)
        raw = (ROOT / name).read_bytes()
        blob = git('rev-parse', ':' + name).decode().strip()
        check(git('cat-file', 'blob', blob) == raw, 'raw index bytes ' + name)
        if re.search(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-(?:proj-)?[A-Za-z0-9_-]{24,})', raw):
            secret_hits.append(name)
        if name not in RECURSIVE:
            files[name] = {'sha256': sha(raw), 'gitBlob': blob, 'bytes': len(raw)}
    check(not secret_hits, 'sensitive pattern scan')
    review = read('docs/p4d-rc1-results/review.json')
    old_snapshot = read(review['finalSnapshot']['path'])
    check(sha((ROOT / review['finalSnapshot']['path']).read_bytes()) == review['finalSnapshot']['sha256'], 'prior final snapshot exact')
    for name, pin in old_snapshot['payload'].items():
        raw = (ROOT / name).read_bytes()
        if name == '.gitattributes':
            check(sha(raw[:pin['bytes']]) == pin['sha256'], 'prior reviewed attribute bytes retained')
        else:
            check(sha(raw) == pin['sha256'] and len(raw) == pin['bytes'], 'prior implementation payload ' + name)
    live = read('docs/p4d-rc1-results/offline-r4.json')
    check(live['sourcePinsBefore'] == live['sourcePinsAfter'], 'actual evidence before/after')
    for name, pin in live['sourcePinsBefore'].items():
        check(sha((ROOT / name).read_bytes()) == pin, 'tested input unchanged ' + name)
    def tree_entries(raw, index=False):
        result = {}
        for entry in filter(None, raw.decode().split('\0')):
            metadata, name = entry.split('\t', 1)
            parts = metadata.split()
            if index:
                check(parts[2] == '0', 'no unresolved index stage ' + name)
                result[name] = (parts[0], parts[1])
            else:
                result[name] = (parts[0], parts[2])
        return result
    head_entries = tree_entries(git('ls-tree', '-r', '-z', '--full-tree', 'HEAD'))
    index_entries = tree_entries(git('ls-files', '--stage', '-z'), index=True)
    unchanged_blobs = 0
    for name, entry in head_entries.items():
        if name not in staged:
            check(index_entries.get(name) == entry, 'unchanged historical Git blob/mode ' + name)
            unchanged_blobs += 1
    with tempfile.TemporaryDirectory(prefix='qa-rc1-index-') as temporary:
        checkout = Path(temporary).resolve()
        check(checkout.is_relative_to(Path(tempfile.gettempdir()).resolve()), 'owned temporary checkout containment')
        git('checkout-index', '--all', '--prefix=' + checkout.as_posix() + '/')
        exact_checkout = staged | set(live['sourcePinsBefore'])
        checked = 0
        for name in sorted(exact_checkout):
            check((checkout / name).read_bytes() == (ROOT / name).read_bytes(), 'fresh index checkout bytes ' + name)
            checked += 1
    whitespace = subprocess.run(['git', 'diff', '--cached', '--check'], cwd=ROOT, capture_output=True)
    check(whitespace.returncode == 0, 'staged whitespace')
    if not args.capture and capture.is_file():
        check(files == json.loads(capture.read_text(encoding='utf-8'))['files'], 'retained staged snapshot exact')
    result = {'version': 'rc1-push-snapshot-1.0.0', 'status': 'FAIL' if failures else 'PASS',
              'baseline': baseline['head'], 'files': files, 'stagedPathsChecked': len(staged),
              'substantivePaths': len(files), 'freshCheckoutPaths': checked,
              'unchangedHeadBlobModes': unchanged_blobs, 'freshCheckoutCoversAllTestedPins': True,
              'originalRawPathsPreserved': len(baseline['files']), 'testedInputPins': len(live['sourcePinsBefore']),
              'secretPatternHits': len(secret_hits), 'stagedDiffCheckExit': whitespace.returncode,
              'uiScreenshots': 'N/A no UI/view/template changes', 'failures': failures}
    if args.capture:
        with capture.open('x', encoding='utf-8', newline='\n') as handle:
            handle.write(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'files'}, ensure_ascii=False, indent=2))
    raise SystemExit(bool(failures))


if __name__ == '__main__':
    main()
