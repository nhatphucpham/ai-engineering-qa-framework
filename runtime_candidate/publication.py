"""Prepare a private replay package and a separately addressable, target-only report."""
from dataclasses import dataclass

from qa_core.application import check_report_package, stage_report_package
from qa_core.rules import AssessmentError

from .blobs import BlobRef, descriptor
from .common import Error, canonical, require, sha, strict_json


@dataclass(frozen=True)
class PreparedPublication:
    package: dict
    private_bytes: bytes
    private_ref: BlobRef
    view: dict
    view_bytes: bytes
    view_ref: BlobRef
    lineage: dict


def _aliases(ids, prefix):
    # The original IDs and even file names may contain restricted user-supplied text.
    return {key: f'{prefix}-{index}' for index, key in enumerate(ids, 1)}


def _mapped(aliases, keys):
    return [aliases[key] for key in keys]


def _projection(package):
    target = package['target']
    content = package['payloads']['prepared']['report']['content']
    results = content['assessment']
    criteria = _aliases((row['criterionId'] for row in results['criteria']), 'criterion')
    constraints = _aliases((row['constraintId'] for row in results['constraints']), 'constraint')
    cited = {key for row in results['criteria'] for key in row['evidenceIds'] + row['contextEvidenceIds']}
    evidence = [row['evidence'] for row in content['evidenceSources'] if row['evidence']['id'] in cited]
    require(all(row['projectId'] == target['projectId'] and row['handoffId'] == target['handoffId']
                for row in evidence), 'E_INTEGRITY')
    refs = _aliases((row['id'] for row in evidence), 'evidence')
    require(set(refs) == cited, 'E_INTEGRITY')
    # Core owns reason codes and action descriptions/doneWhen. Some ownerRole values
    # come from requirement authors; map those onto a bounded set of routing labels.
    roles = {'developer', 'qa', 'check-owner', 'coverage-policy-owner', 'constraint-review-owner',
             'owner', 'reviewer', 'product-owner'}
    view = {
        'viewVersion': '1.0.0', 'runId': target['runId'], 'reportId': target['reportId'],
        **{key: results[key] for key in ('evaluationMode', 'statusScope', 'verification',
                                         'hasUnverifiedMandatory', 'hasOpenMandatoryCoverage', 'humanDecision')},
        'pendingConstraintIds': _mapped(constraints, results['pendingConstraintIds']),
        'criteria': [{
            'criterionId': criteria[row['criterionId']], 'status': row['status'],
            'reasonCodes': list(row['reasonCodes']), 'hasOpenCoverage': row['hasOpenCoverage'],
            'evidenceIds': _mapped(refs, row['evidenceIds']),
            'contextEvidenceIds': _mapped(refs, row['contextEvidenceIds']),
        } for row in results['criteria']],
        'constraints': [{'constraintId': constraints[row['constraintId']], 'status': row['status'],
                         'reasonCode': row['reasonCode']} for row in results['constraints']],
        'actions': [{
            'id': action['id'], 'criterionIds': _mapped(criteria, action['criterionIds']),
            'constraintIds': _mapped(constraints, action['constraintIds']),
            'ownerRole': action['ownerRole'] if action['ownerRole'] in roles else 'requirement-owner',
            'state': action['state'], 'description': action['description'], 'doneWhen': action['doneWhen'],
        } for action in content['actions']],
        'sources': [{
            'id': refs[row['id']], 'classification': 'derived_evidence_metadata',
            'level': row['level'], 'outcome': row['outcome'], 'provenanceKind': row['provenance']['kind'],
            'candidateRevisionMatch': row['revision'] == target['candidateRevision'],
        } for row in evidence],
        'legacyProjection': {'status': content['legacyProjection']['status'],
                             'reasonCodes': list(content['legacyProjection']['reasonCodes'])},
    }
    # Keep the reverse lookup private. The server can join it to separately registered
    # project/task/revision and source classification before releasing safe source bytes.
    lineage = {kind: {alias: original for original, alias in mapping.items()}
               for kind, mapping in [('criteria', criteria), ('constraints', constraints), ('evidence', refs)]}
    return view, lineage


def prepare(bundle, assessment, *, expected_bundle_digest: str, expected_assessment_digest: str,
            run_id: str, report_id: str) -> PreparedPublication:
    """Use caller-held pins and issuer-bound IDs. Only view_bytes is ordinary report content."""
    bundle_bytes, assessment_bytes = canonical(bundle), canonical(assessment)
    require(sha(bundle_bytes) == expected_bundle_digest and sha(assessment_bytes) == expected_assessment_digest,
            'E_INTEGRITY')
    try:
        package = stage_report_package(strict_json(bundle_bytes), strict_json(assessment_bytes),
                                       run_id=run_id, report_id=report_id)
        diagnostics = check_report_package(package, expected_bundle_sha256=expected_bundle_digest,
                                           expected_assessment_sha256=expected_assessment_digest,
                                           run_id=run_id, report_id=report_id)
        require(not diagnostics, 'E_INTEGRITY')
        view, lineage = _projection(package)
    except (AssessmentError, KeyError, TypeError, IndexError, StopIteration, RecursionError):
        raise Error('E_INTEGRITY') from None
    private_bytes = canonical(package)
    view_bytes = canonical(view)
    return PreparedPublication(package, private_bytes, descriptor(private_bytes),
                               view, view_bytes, descriptor(view_bytes), lineage)
