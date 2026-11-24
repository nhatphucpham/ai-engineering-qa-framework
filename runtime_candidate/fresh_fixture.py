"""Register source-only MOCK-06 input. No historical observation/assessment is loaded."""
from datetime import datetime, timezone
from pathlib import Path

from qa_core.contracts import validate
from .common import require, sha

ROOT = Path(__file__).resolve().parents[1]


def source_intake(*, project_id, task_id, handoff_id, run_id, config_version=2, policy_version=2):
    from spikes.vf1.core_bridge import ARTIFACT_KINDS, LEVELS, contract_bundle, requirement_row, EXECUTION_ARTIFACT, POLICY_ARTIFACT
    from spikes.vf1.run_vf1 import CASE
    artifacts, sources = {}, {}
    for index, (relative, kind) in enumerate(ARTIFACT_KINDS.items(), 1):
        raw = (CASE / relative).read_bytes()
        aid = 'artifact-' + str(index)
        artifacts[aid] = {'id': aid, 'kind': kind, 'relativePath': relative, 'sha256': sha(raw), 'text': raw.decode('utf-8')}
        revision = 'mock-req-06-v1' if kind == 'requirement' else 'mock-06-head-v1'
        sources[aid] = (raw, 'safe_source', revision)
    requirement = artifacts['artifact-1']
    criteria = [{'id': cid, 'expected': requirement_row(requirement, cid)[1], 'locator': cid} for cid in LEVELS]
    # Reuse only the structural source importer. Its synthetic execution slots are
    # immediately removed; no timestamp/outcome/lease or fake raw record is persisted.
    source_context = {'runId': run_id, 'jobId': handoff_id, 'observedAt': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                      'executionSha256': '0' * 64, 'selectedCriteria': criteria}
    bundle = contract_bundle(source_context, {'risk': {'rationale': 'Source-only intake; current execution and assessment are not yet available.'},
                                              'bindings': []}, artifacts, requirement, {})
    bundle['artifacts'] = [row for row in bundle['artifacts'] if row['id'] not in (EXECUTION_ARTIFACT, POLICY_ARTIFACT)]
    bundle['specimenNotice'] = 'Synthetic source-only intake; no execution observation or accepted assessment has been imported.'
    for project in bundle['projects']:
        project.update(id=project_id, configVersion=config_version)
        project['dataPolicy'].update(version=policy_version, allowedPaths=list(ARTIFACT_KINDS))
    for key in ('tasks', 'artifacts', 'handoffs', 'runs'):
        for row in bundle[key]:
            row['projectId'] = project_id
            if key == 'tasks':
                row['id'] = task_id
            if 'taskRef' in row:
                row['taskRef'] = task_id
            if key == 'runs':
                row.update(state='queued', attempt=0, lease=None, projectConfigVersion=config_version, dataPolicyVersion=policy_version)
    require(not validate(bundle) and bundle['evidence'] == [] and bundle['reports'] == [] and bundle['workerResults'] == [], 'E_INTEGRITY')
    hashes = {'case/' + row['relativePath']: row['sha256'] for row in artifacts.values()}
    hashes['test_worker.py'] = sha((ROOT / 'spikes/vf1/test_worker.py').read_bytes())
    return {'bundle': bundle, 'sources': sources,
            'manifest': {'origin': 'fresh-approved-source-only', 'mode': 'executed_fixture',
                         'candidateRevision': 'mock-06-head-v1', 'requirementVersion': 'mock-req-06-v1',
                         'artifactHashes': {row['relativePath']: row['sha256'] for row in artifacts.values()},
                         'inputHashes': hashes, 'checkRegistry': 'vf1-fixed-1.0.0'}}
