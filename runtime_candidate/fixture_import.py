"""Operator-side synthetic HC1 import fixture. The service never imports this module."""
from pathlib import Path

from .common import digest, require, sha, strict_json


ROOT = Path(__file__).resolve().parent.parent
REVIEW_PATH = 'docs/hc1-results/hc1-20261118-r1/review-snapshot-r1.json'
REVIEW_SHA = 'f02dc4979536c862dd8e0dad64382c8afa9e1cf12bd7eabb439604cd30266729'
ARCHIVE = 'docs/hc1-results/hc1-20261118-live-r3'
TEXT_IDS = frozenset(f'artifact-{i}' for i in range(1, 9))
FILES = ('anchors.json', 'dispatch.json', 'host-request.json', 'execution.json',
         'accepted/receipt.json', 'accepted/bundle.json', 'accepted/assessment.json')


def load_hc1(label, *, config_version=2, policy_version=2, include_canaries=False):
    """Return an unregistered historic specimen and unaccepted assessment candidate."""
    require(isinstance(label, str) and label in ('a', 'A', 'b', 'B'))
    require(all(type(n) is int and 0 < n <= 2147483647 for n in (config_version, policy_version)))
    require(type(include_canaries) is bool)
    label = label.lower()
    origin = f'{ARCHIVE}/{label}'
    review_raw = (ROOT / REVIEW_PATH).read_bytes()
    require(sha(review_raw) == REVIEW_SHA, 'E_INTEGRITY')
    pins = strict_json(review_raw)['files']
    paths = [f'{origin}/{filename}' for filename in FILES] + [f'{ARCHIVE}/caller-tickets.json']
    source_pins = {}
    archive_bytes = {}
    for path in paths:
        raw = (ROOT / path).read_bytes()
        require(path in pins and sha(raw) == pins[path], 'E_INTEGRITY')
        source_pins[path] = pins[path]
        archive_bytes[path] = raw

    def read(name):
        return strict_json(archive_bytes[f'{origin}/{name}'])

    receipt = read('accepted/receipt.json')
    bundle = read('accepted/bundle.json')
    assessment = read('accepted/assessment.json')
    job = read('host-request.json')
    anchors = read('anchors.json')
    tickets = strict_json(archive_bytes[f'{ARCHIVE}/caller-tickets.json'])
    run, = bundle['runs']
    project, = bundle['projects']
    require(receipt['runId'] == job['runId'] == anchors['runId'] == run['id'], 'E_INTEGRITY')
    require(project['id'] == run['projectId'] == assessment['projectId'], 'E_INTEGRITY')
    require(job['jobId'] == anchors['jobId'] == assessment['handoffId'] == run['handoffId'], 'E_INTEGRITY')
    require(job['candidateRevision'] == assessment['candidateRevision'] == run['candidateRevision'], 'E_INTEGRITY')
    require(receipt['dispatchDigest'] == tickets[label] == pins[f'{origin}/dispatch.json'], 'E_INTEGRITY')
    require(receipt['jobDigest'] == anchors['jobDigest'] == pins[f'{origin}/host-request.json'], 'E_INTEGRITY')
    require(job['executionSha256'] == anchors['executionSha256'] == pins[f'{origin}/execution.json'], 'E_INTEGRITY')
    require(receipt['files']['bundle.json'] == digest(bundle) and
            receipt['files']['assessment.json'] == digest(assessment), 'E_INTEGRITY')

    content = {}
    for row in job['artifacts']:
        raw = row['text'].encode('utf-8')
        require(row['id'] not in content and sha(raw) == row['sha256'], 'E_INTEGRITY')
        content[row['id']] = (raw, 'safe_source')
    require(content.keys() == TEXT_IDS, 'E_INTEGRITY')
    content['vf1-execution-record'] = (archive_bytes[f'{origin}/execution.json'], 'restricted')
    content['vf1-coverage-policy'] = (archive_bytes[f'{origin}/host-request.json'], 'restricted')
    sources = {}
    for artifact in bundle['artifacts']:
        aid = artifact['id']
        require(artifact['projectId'] == project['id'] and aid in content and aid not in sources, 'E_INTEGRITY')
        raw, classification = content[aid]
        require(sha(raw) == artifact['sha256'], 'E_INTEGRITY')
        sources[aid] = (raw, classification, artifact['revision'])
    require(sources.keys() == content.keys(), 'E_INTEGRITY')
    if include_canaries:
        for aid, classification in (('fixture-raw-canary', 'raw_secret'), ('fixture-taint-canary', 'tainted')):
            sources[aid] = (('DUMMY-M50-' + aid).encode('ascii'), classification, 'm50-canary-v1')

    fields = (
        ('bundle.projects[0].configVersion', project, 'configVersion', config_version),
        ('bundle.projects[0].dataPolicy.version', project['dataPolicy'], 'version', policy_version),
        ('bundle.runs[0].projectConfigVersion', run, 'projectConfigVersion', config_version),
        ('bundle.runs[0].dataPolicyVersion', run, 'dataPolicyVersion', policy_version),
        ('assessment.projectConfigVersion', assessment, 'projectConfigVersion', config_version),
        ('assessment.dataPolicyVersion', assessment, 'dataPolicyVersion', policy_version),
    )
    changes = []
    for path, obj, key, target in fields:
        require(type(obj[key]) is int and obj[key] == 1, 'E_INTEGRITY')
        if target != obj[key]:
            changes.append({'field': path, 'from': obj[key], 'to': target})
            obj[key] = target
    provenance = {
        'version': 'hc1-import-1.0.0', 'importedTrue': True, 'origin': origin,
        'reviewManifest': {'path': REVIEW_PATH, 'sha256': REVIEW_SHA}, 'originalFileDigests': source_pins,
        'historicalDispatchDigest': tickets[label], 'historicalObservedAt': job['observedAt'],
        'metadataChanges': changes, 'bundleDigest': digest(bundle), 'assessmentDigest': digest(assessment),
        'extraSyntheticSourceIds': sorted(sources.keys() - content.keys()),
    }
    return {'project': project['id'], 'run_id': run['id'], 'bundle': bundle, 'assessment': assessment,
            'sources': sources, 'provenance': provenance}
