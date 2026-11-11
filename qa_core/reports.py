"""Synthetic offline report oracle over supplied judgments; no runtime or P1 export."""

import copy
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator

from .rules import AssessmentError, ROOT, evaluate
from .contracts import FORMATS


SCHEMA = json.loads((ROOT / 'schemas/qa-offline-report-v1.schema.json').read_text(encoding='utf-8'))
Draft202012Validator.check_schema(SCHEMA)
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FORMATS)


def digest(value):
    """Versioned Python serialization, deliberately not RFC 8785/JCS or attestation."""
    payload = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def create_report(bundle, assessment):
    if not isinstance(assessment, dict) or assessment.get('assessmentVersion') != '2.0.0':
        raise AssessmentError([{'code': 'E_REPORT_ASSESSMENT_VERSION',
                                'message': 'Reference reports require assessment 2.0.0; no implicit upgrade'}])
    try:
        bindings = {'algorithm': 'sha256-python-json-v1', 'bundleSha256': digest(bundle),
                    'assessmentSha256': digest(assessment)}
    except (TypeError, ValueError, UnicodeError, RecursionError):
        raise AssessmentError([{'code': 'E_INPUT_CANONICAL', 'message': 'Input is not supported finite JSON'}]) from None
    result = evaluate(bundle, assessment)
    handoff = next(h for h in bundle['handoffs'] if h['id'] == assessment['handoffId'])
    plans = {p['criterionId']: p for p in assessment['criteria']}
    reviews = {r['constraintId']: r for r in assessment['constraintReviews']}
    evidence_reviews = {r['evidenceId']: r for r in assessment['evidenceReviews']}
    criteria = {c['id']: c for c in handoff['criteria']}
    actions = []

    def action(criterion_ids, constraint_ids, role, description, done_when):
        actions.append({'id': 'action-' + str(len(actions) + 1), 'criterionIds': criterion_ids,
                        'constraintIds': constraint_ids, 'ownerRole': role, 'assigneeRef': None,
                        'state': 'proposed', 'description': description, 'doneWhen': done_when})

    for item in result['criteria']:
        cid = item['criterionId']
        reasons = set(item['reasonCodes'])
        if item['status'] == 'failed':
            action([cid], [], 'developer', 'Review the current counterexample against the requirement.',
                   'Resolve or dispute the sourced counterexample; provide fresh evidence in a new assessment.')
        if item['status'] not in ('unverified', 'failed'):
            continue
        if item['status'] == 'failed' and not item['hasOpenCoverage']:
            continue
        # Independent blockers need independent proposals; one priority branch must not hide another.
        before_gaps = len(actions)
        if reasons & {'REQUIREMENT_AMBIGUOUS', 'REQUIREMENT_CONFLICT'}:
            action([cid], [], criteria[cid]['ownerRole'],
                   'Resolve the expected behavior using the cited requirement sources.',
                   'Provide an authorized clarification in a new requirement/handoff snapshot, then re-evaluate.')
        if reasons & {'NA_PENDING', 'NA_CONTRADICTED'}:
            action([cid], [], criteria[cid]['ownerRole'],
                   'Obtain a sourced applicability decision and address any cited contrary evidence.',
                   'Provide an authorized applicability decision with actor/source on the same candidate and re-evaluate; '
                   'version requirements only if expected behavior changes.')
        if 'EVIDENCE_CONFLICT' in reasons:
            action([cid], [], 'qa', 'Investigate the contradictory evidence in its comparison context.',
                   'Resolve contradictory evidence and account for required levels/contexts on this candidate.')
        if reasons & {'OUTCOME_BLOCKED', 'OUTCOME_ERROR', 'OUTCOME_SKIPPED', 'OUTCOME_NOT_RUN', 'OUTCOME_UNKNOWN'}:
            action([cid], [], 'check-owner',
                   'Resolve the recorded check environment, permission or execution precondition.',
                   'Resolve the recorded check outcome reason, rerun the approved check on this candidate, '
                   'and attach eligible evidence before re-evaluation.')
        if 'COVERAGE_PLAN_PENDING' in reasons:
            action([cid], [], 'coverage-policy-owner', 'Resolve the scoped risk and coverage-plan decision.',
                   'Provide an accepted, sourced risk/coverage plan without expanding the run scope, then re-evaluate.')
        review_reasons = reasons & {
            'OUTCOME_RELATION_MISMATCH', 'INCONCLUSIVE_BINDING', 'JUDGMENT_PENDING', 'JUDGMENT_DISPUTED',
            'EVIDENCE_REVIEW_MISSING', 'INTEGRITY_UNRESOLVED', 'ATTRIBUTION_UNRESOLVED', 'SCOPE_UNRESOLVED',
            'PROVENANCE_NOT_ALLOWED', 'RECORD_IS_NOT_EXECUTION', 'STALE_EVIDENCE',
        }
        if review_reasons:
            action([cid], [], 'qa', 'Review the evidence binding, provenance or acceptance: ' + ', '.join(sorted(review_reasons)),
                   'Resolve the cited mapping/review issue against actual outcomes and current sources; '
                   'provide an appropriately sourced assessment and re-evaluate.')
        if len(actions) == before_gaps:
            action([cid], [], 'qa', 'Complete the remaining required evidence levels and comparison contexts.',
                   'Supply current, appropriately reviewed evidence for every still-unchecked declared level/context; re-evaluate.')
    for item in result['constraints']:
        if item['status'] == 'pending':
            declaration = next(c for c in handoff['constraints'] if c['id'] == item['constraintId'])
            done_when = ('Obtain an authorized resolution and a new handoff snapshot with a resolved declaration, '
                         'plus an accepted review with actor/source/current candidate; re-evaluate.'
                         if declaration['state'] == 'pending' else
                         'Provide an accepted review with actor/source/current candidate, then re-evaluate.')
            action([], [item['constraintId']], 'constraint-review-owner',
                   'Obtain the scoped constraint review; a declared state alone is insufficient.',
                   done_when)

    declared_pending = any(c['mandatory'] and c['state'] == 'pending' for c in handoff['constraints'])
    legacy_summary = ('failed' if any(c['status'] == 'failed' for c in result['criteria']) else
                      'incomplete' if result['hasUnverifiedMandatory'] or declared_pending else 'complete')
    legacy_reasons = ['P1_V2_EXPORT_NOT_IMPLEMENTED']
    if legacy_summary != result['verification']:
        legacy_reasons.append('P1_V2_CONSTRAINT_COLLISION')
    selected_evidence = [e for e in bundle['evidence']
                         if e['projectId'] == handoff['projectId'] and e['handoffId'] == handoff['id']]
    artifact_ids = {assessment['policySourceArtifactId']}
    for criterion in handoff['criteria']:
        artifact_ids.update(c['artifactId'] for c in criterion['claims'])
        plan = plans[criterion['id']]
        artifact_ids.update(o['sourceArtifactId'] for o in plan['obligations'])
        artifact_ids.update(c['sourceArtifactId'] for c in plan['comparisonContexts'])
        if plan['naDecision'] and plan['naDecision']['sourceArtifactId']:
            artifact_ids.add(plan['naDecision']['sourceArtifactId'])
    artifact_ids.update(e['provenance']['sourceArtifactId'] for e in selected_evidence)
    artifact_ids.update(c['sourceArtifactId'] for c in handoff['constraints'])
    artifact_ids.update(i['sourceArtifactId'] for i in handoff['knownIssues'])
    artifact_ids.update(handoff['sourceArtifactIds'] + handoff['diffArtifactIds'])
    artifact_ids.update(r['sourceArtifactId'] for r in assessment['constraintReviews'] if r['sourceArtifactId'])
    report = {
        'reportVersion': '1.0.0', 'classification': 'synthetic-only', 'processingStatus': 'reference_report',
        'inputBindings': bindings,
        'scope': {key: assessment[key] for key in ('projectId', 'handoffId', 'candidateRevision',
                  'projectConfigVersion', 'dataPolicyVersion', 'policySourceArtifactId', 'assessorRef')},
        'assessment': result,
        'assessmentContext': {'risk': assessment['risk'], 'bindings': assessment['bindings']},
        'handoffContext': {key: handoff[key] for key in ('intake', 'decisionMoment', 'requestedDecision',
                          'actors', 'riskRationale', 'stageRecords', 'knownIssues', 'sourceArtifactIds', 'diffArtifactIds')},
        'criterionSources': [{'criterion': c, 'plan': plans[c['id']]} for c in handoff['criteria']],
        'constraintSources': [{'declaration': c, 'review': reviews.get(c['id'])} for c in handoff['constraints']],
        'evidenceSources': [{'evidence': e, 'review': evidence_reviews.get(e['id'])} for e in selected_evidence],
        'artifacts': [a for a in bundle['artifacts'] if a['id'] in artifact_ids],
        'actions': actions, 'legacyProjection': {'status': 'projection_unsupported', 'reasonCodes': legacy_reasons},
        'limitations': ['Synthetic reference report over supplied judgments; no authenticated authority or domain truth.',
                        'No project tests, model/network calls, persistence, P1 export or run lifecycle performed.',
                        'Digests identify supplied JSON inputs, not source contents, actor authenticity or trust.',
                        'Proposed role labels are routing suggestions; no assignee, approval or action completion asserted.'],
    }
    report['scope'].update(taskRef=handoff['taskRef'], requirementVersion=handoff['requirementVersion'])
    # Detach all source objects so a consumer cannot mutate inputs through the report.
    report = copy.deepcopy(report)
    if list(VALIDATOR.iter_errors(report)):
        raise AssessmentError([{'code': 'E_REPORT_PROJECTION', 'message': 'Reference report cannot represent input'}])
    return report


def validate_report(report, bundle, assessment):
    """Check shape, binding and exact derivation; does not authenticate supplied inputs."""
    if list(VALIDATOR.iter_errors(report)):
        return [{'code': 'E_REPORT_SCHEMA', 'message': 'Unsupported reference report shape or version'}]
    try:
        expected = create_report(bundle, assessment)
    except AssessmentError:
        return [{'code': 'E_REPORT_INPUT', 'message': 'Cannot derive report from supplied inputs'}]
    try:
        if digest(report) != digest(expected):
            return [{'code': 'E_REPORT_DERIVATION', 'message': 'Report differs from the bound input and rule derivation'}]
    except (TypeError, ValueError, UnicodeError, RecursionError):
        return [{'code': 'E_REPORT_DERIVATION', 'message': 'Report is not supported finite JSON'}]
    return []
