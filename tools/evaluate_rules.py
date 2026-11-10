"""P2 offline reference semantics over supplied judgments; not a production QA engine."""

import argparse
import json
from pathlib import Path

from jsonschema import Draft202012Validator

from json_input import load_json
from validate_contracts import ROOT, validate


SCHEMA = json.loads((ROOT / 'schemas/qa-assessment-v1.schema.json').read_text(encoding='utf-8'))
Draft202012Validator.check_schema(SCHEMA)
ASSESSMENT_VALIDATOR = Draft202012Validator(SCHEMA)
SCHEMA_V2 = json.loads((ROOT / 'schemas/qa-assessment-v2.schema.json').read_text(encoding='utf-8'))
Draft202012Validator.check_schema(SCHEMA_V2)
ASSESSMENT_VALIDATOR_V2 = Draft202012Validator(SCHEMA_V2)
LIFECYCLE_VALIDATOR = Draft202012Validator({'$ref': '#/$defs/lifecycleContext', '$defs': SCHEMA['$defs']})
RULES_VERSION = 'p2-rules-1.0.0'


class AssessmentError(ValueError):
    def __init__(self, errors):
        super().__init__('Invalid contract or assessment input')
        self.errors = errors


def evaluate(bundle, assessment):
    v2 = isinstance(assessment, dict) and assessment.get('assessmentVersion') == '2.0.0'
    validator = ASSESSMENT_VALIDATOR_V2 if v2 else ASSESSMENT_VALIDATOR
    errors = validate(bundle)
    for error in validator.iter_errors(assessment):
        errors.append({'code': 'E_ASSESSMENT_SCHEMA', 'path': '/' + '/'.join(map(str, error.absolute_path)),
                       'message': 'Assessment schema constraint failed: ' + str(error.validator)})
    if errors:
        raise AssessmentError(errors)

    def invalid(code, message):
        errors.append({'code': code, 'message': message})

    project = next((p for p in bundle['projects'] if p['id'] == assessment['projectId']), None)
    handoff = next((h for h in bundle['handoffs'] if h['id'] == assessment['handoffId']), None)
    if not project or not handoff or handoff['projectId'] != project['id']:
        raise AssessmentError([{'code': 'E_ASSESSMENT_REFERENCE', 'message': 'Assessment project/handoff mismatch'}])
    if (assessment['candidateRevision'] != handoff['candidateRevision']
            or assessment['projectConfigVersion'] != project['configVersion']
            or assessment['dataPolicyVersion'] != project['dataPolicy']['version']):
        invalid('E_ASSESSMENT_VERSION', 'Assessment does not match frozen candidate/project/policy')
    artifacts = {a['id']: a for a in bundle['artifacts']}

    def artifact_ok(aid):
        artifact = artifacts.get(aid)
        return artifact and artifact['projectId'] == project['id'] and artifact['taskRef'] in (None, handoff['taskRef'])

    if not artifact_ok(assessment['policySourceArtifactId']):
        invalid('E_ASSESSMENT_REFERENCE', 'Policy reference is absent or out of scope')
    criteria = {c['id']: c for c in handoff['criteria']}
    plans = {p['criterionId']: p for p in assessment['criteria']}
    if len(plans) != len(assessment['criteria']) or set(plans) != set(criteria):
        invalid('E_ASSESSMENT_COVERAGE', 'Declare exactly one plan for every criterion')
    for plan in assessment['criteria']:
        ids = [o['id'] for o in plan['obligations']]
        if len(ids) != len(set(ids)):
            invalid('E_ASSESSMENT_REFERENCE', 'Obligation IDs must be unique per criterion')
        if any(not artifact_ok(o['sourceArtifactId']) for o in plan['obligations']):
            invalid('E_ASSESSMENT_REFERENCE', 'Obligation source is absent or out of scope')
        contexts = {c['id']: c for c in plan['comparisonContexts']}
        if len(contexts) != len(plan['comparisonContexts']):
            invalid('E_ASSESSMENT_CONTEXT', 'Comparison contexts must be unique per criterion')
        if any(not artifact_ok(c['sourceArtifactId']) for c in plan['comparisonContexts']):
            invalid('E_ASSESSMENT_REFERENCE', 'Comparison-context source is absent or out of scope')
        if any(not set(o['requiredComparisonKeys']) <= set(contexts) for o in plan['obligations']):
            invalid('E_ASSESSMENT_CONTEXT', 'Required comparison context must be described and sourced')
        na = plan['naDecision']
        if plan['applicability'] == 'applicable' and na is not None:
            invalid('E_ASSESSMENT_APPLICABILITY', 'Applicable criterion cannot carry a contrary N/A decision')
        if na and na['sourceArtifactId'] and not artifact_ok(na['sourceArtifactId']):
            invalid('E_ASSESSMENT_REFERENCE', 'N/A decision source is absent or out of scope')
    evidence = {e['id']: e for e in bundle['evidence'] if e['projectId'] == project['id'] and e['handoffId'] == handoff['id']}
    reviews = {r['evidenceId']: r for r in assessment['evidenceReviews']}
    if len(reviews) != len(assessment['evidenceReviews']) or not set(reviews) <= set(evidence):
        invalid('E_ASSESSMENT_REFERENCE', 'Evidence reviews must be unique and in this handoff')
    binding_keys = []
    for binding in assessment['bindings']:
        plan = plans.get(binding['criterionId'])
        ev = evidence.get(binding['evidenceId'])
        if (not plan or not ev or binding['criterionId'] not in ev['criterionIds']
                or binding['obligationId'] not in {o['id'] for o in plan['obligations']}):
            invalid('E_ASSESSMENT_REFERENCE', 'Binding must reference its criterion, obligation and mapped evidence')
        elif binding['relation'] == 'supports':
            obligation = next(o for o in plan['obligations'] if o['id'] == binding['obligationId'])
            if binding['comparisonKey'] not in obligation['requiredComparisonKeys']:
                invalid('E_ASSESSMENT_REFERENCE', 'Positive coverage must map to a declared comparison context')
        if plan and binding['comparisonKey'] not in {c['id'] for c in plan['comparisonContexts']}:
            invalid('E_ASSESSMENT_CONTEXT', 'All bindings including counterexamples require a sourced comparison context')
        binding_keys.append((binding['criterionId'], binding['obligationId'], binding['evidenceId'], binding['comparisonKey']))
    if len(binding_keys) != len(set(binding_keys)):
        invalid('E_ASSESSMENT_BINDING', 'Do not assert multiple relationships for the same binding')
    constraints = {c['id']: c for c in handoff['constraints']}
    constraint_reviews = {r['constraintId']: r for r in assessment['constraintReviews']}
    if len(constraint_reviews) != len(assessment['constraintReviews']) or not set(constraint_reviews) <= set(constraints):
        invalid('E_ASSESSMENT_REFERENCE', 'Constraint reviews must be unique and declared')
    for review in assessment['constraintReviews']:
        if review['sourceArtifactId'] and not artifact_ok(review['sourceArtifactId']):
            invalid('E_ASSESSMENT_REFERENCE', 'Constraint-review source is absent or out of scope')
    if errors:
        raise AssessmentError(errors)

    record_mode = assessment['evaluationMode'] == 'record_review'

    def effective_level(ev):
        if v2 and ev['provenance']['kind'] == 'source_reasoning':
            return 'source_review'
        return ev['level']

    results = []
    for cid, criterion in criteria.items():
        plan = plans[cid]
        reasons, decisive, context = set(), set(), set()
        supports = {o['id']: {} for o in plan['obligations']}
        violates = {o['id']: {} for o in plan['obligations']}
        for binding in (b for b in assessment['bindings'] if b['criterionId'] == cid):
            ev = evidence[binding['evidenceId']]
            review = reviews.get(ev['id'])
            reason = None
            if binding['judgment'] != 'accepted':
                reason = 'JUDGMENT_PENDING' if binding['judgment'] == 'candidate' else 'JUDGMENT_DISPUTED'
            elif ev['revision'] != handoff['candidateRevision']:
                reason = 'STALE_EVIDENCE'
            elif not review:
                reason = 'EVIDENCE_REVIEW_MISSING'
            elif review['integrity'] != 'matched':
                reason = 'INTEGRITY_UNRESOLVED'
            elif review['attribution'] != 'accepted':
                reason = 'ATTRIBUTION_UNRESOLVED'
            elif review['scope'] != 'accepted':
                reason = 'SCOPE_UNRESOLVED'
            elif ev['provenance']['kind'] not in plan['allowedProvenance']:
                reason = 'PROVENANCE_NOT_ALLOWED'
            elif not record_mode and ev['provenance']['kind'] not in ('execution', 'source_reasoning'):
                reason = 'RECORD_IS_NOT_EXECUTION'
            elif ev['outcome'] not in ('pass', 'fail'):
                reason = 'OUTCOME_' + ev['outcome'].upper()
            elif binding['relation'] == 'inconclusive':
                reason = 'INCONCLUSIVE_BINDING'
            elif (binding['relation'] == 'supports') != (ev['outcome'] == 'pass'):
                reason = 'OUTCOME_RELATION_MISMATCH'
            if reason:
                reasons.add(reason)
                context.add(ev['id'])
                continue
            decisive.add(ev['id'])
            destination = supports if binding['relation'] == 'supports' else violates
            destination[binding['obligationId']].setdefault(binding['comparisonKey'], []).append(ev)

        conflicts = {(oid, key) for oid, cases in violates.items() for key in cases if supports[oid].get(key)}
        clear_violations = {(oid, key) for oid, cases in violates.items() for key in cases if (oid, key) not in conflicts}
        missing, open_checks = set(), set()
        for obligation in plan['obligations']:
            oid = obligation['id']
            for key in obligation['requiredComparisonKeys']:
                matches = supports[oid].get(key, [])
                checked = matches + violates[oid].get(key, [])
                required = set(plan['requiredLevels'])
                if not matches or not required <= {effective_level(e) for e in matches}:
                    missing.add((oid, key))
                if not checked or not required <= {effective_level(e) for e in checked}:
                    open_checks.add((oid, key))
        plan_pending = (plan['planState'] != 'accepted' or assessment['risk']['state'] != 'accepted'
                        or assessment['risk']['tier'] == 'unknown')
        open_parts = bool(open_checks or conflicts or plan_pending)
        if v2 and conflicts:
            reasons.add('EVIDENCE_CONFLICT')
        if plan_pending:
            reasons.add('COVERAGE_PLAN_PENDING')
        na = plan['naDecision']
        decision_bound = (na and na['actorRef'] and na['sourceArtifactId']
                          and na['candidateRevision'] == handoff['candidateRevision'])
        rejected_na = plan['applicability'] == 'not_applicable_requested' and decision_bound and na['state'] == 'rejected'
        if rejected_na:
            reasons.add('NA_REJECTED_CHECK_AS_APPLICABLE')
        if criterion['clarification'] != 'clear':
            status = 'unverified'
            reasons.add('REQUIREMENT_' + criterion['clarification'].upper())
        elif plan['applicability'] == 'not_applicable_requested' and not rejected_na:
            accepted_na = decision_bound and na['state'] == 'accepted'
            if accepted_na and not clear_violations and not conflicts:
                status, open_parts = 'not_applicable', False
                reasons.add('NA_ACCEPTED')
            else:
                status = 'unverified'
                reasons.add('NA_CONTRADICTED' if accepted_na else 'NA_PENDING')
        elif clear_violations:
            status = 'failed'
            reasons.add('CURRENT_BEHAVIOR_VIOLATION')
        elif conflicts:
            status = 'unverified'
            reasons.add('EVIDENCE_CONFLICT')
        elif plan_pending:
            status = 'unverified'
            reasons.add('COVERAGE_PLAN_PENDING')
        elif missing:
            status = 'unverified'
            reasons.add('REQUIRED_COVERAGE_MISSING')
        else:
            status, open_parts = 'verified', False
            reasons.add('SCOPED_COVERAGE_SATISFIED')
        if record_mode:
            reasons.add('RECORD_SCOPE_ONLY')
        context -= decisive
        results.append({'criterionId': cid, 'status': status, 'reasonCodes': sorted(reasons),
                        'evidenceIds': sorted(decisive), 'contextEvidenceIds': sorted(context),
                        'hasOpenCoverage': open_parts, 'scopeDescription': plan['scopeDescription']})

    constraint_results = []
    for constraint in handoff['constraints']:
        review = constraint_reviews.get(constraint['id'])
        bound_review = (review and review['judgment'] == 'accepted' and review['actorRef']
                        and review['sourceArtifactId'] == constraint['sourceArtifactId']
                        and review['candidateRevision'] == handoff['candidateRevision'])
        status = constraint['state'] if constraint['state'] != 'pending' and bound_review else 'pending'
        constraint_results.append({'constraintId': constraint['id'], 'status': status,
                                   'reasonCode': 'CONSTRAINT_REVIEW_ACCEPTED' if status != 'pending' else 'CONSTRAINT_PENDING'})
    pending_constraints = [c['constraintId'] for c in constraint_results if c['status'] == 'pending' and constraints[c['constraintId']]['mandatory']]
    unverified = any(criteria[r['criterionId']]['mandatory'] and r['status'] == 'unverified' for r in results)
    open_mandatory_parts = any(criteria[r['criterionId']]['mandatory'] and r['hasOpenCoverage'] for r in results)
    failed = any(r['status'] == 'failed' for r in results)
    summary = 'failed' if failed else ('incomplete' if unverified or pending_constraints else 'complete')
    return {'rulesVersion': 'p2-rules-2.0.0' if v2 else RULES_VERSION, 'processingStatus': 'evaluated', 'evaluationMode': assessment['evaluationMode'],
            'statusScope': 'record_only' if record_mode else 'candidate_scoped_assessment',
            'verification': summary, 'hasUnverifiedMandatory': unverified,
            'hasOpenMandatoryCoverage': open_mandatory_parts, 'pendingConstraintIds': pending_constraints,
            'criteria': results, 'constraints': constraint_results, 'humanDecision': 'pending',
            'limitations': ['Offline reference semantics over supplied assessment judgments, not authenticated trust or domain truth.',
                            'No test execution, model calls, auth, report persistence or runtime enforcement performed.']}


def validate_transition(entity, current, target, context):
    """Check a proposed lifecycle transition over supplied context, without changing records."""
    if list(LIFECYCLE_VALIDATOR.iter_errors(context)):
        return ['TRANSITION_CONTEXT_INVALID']
    finding = {
        'candidate': {'confirmed', 'rejected', 'duplicate', 'disputed'},
        'pending': {'confirmed', 'rejected', 'duplicate', 'disputed'},
        'disputed': {'confirmed', 'rejected', 'duplicate'},
        'confirmed': {'disputed'}, 'rejected': {'disputed'}, 'duplicate': {'disputed'},
    }
    action = {'proposed': {'assigned', 'blocked'}, 'assigned': {'in_progress', 'blocked'},
              'in_progress': {'done', 'blocked'}, 'blocked': {'assigned', 'in_progress'}, 'done': {'assigned'}}
    table = finding if entity == 'finding' else action if entity == 'action' else {}
    errors = []
    if target not in table.get(current, set()):
        errors.append('TRANSITION_NOT_ALLOWED')
    if not context.get('authorized'):
        errors.append('ACTOR_NOT_AUTHORIZED')
    if not context.get('rationale'):
        errors.append('RATIONALE_REQUIRED')
    if entity == 'finding' and target in ('confirmed', 'rejected', 'duplicate'):
        if context.get('basisState') != 'accepted' or not context.get('basisRefs'):
            errors.append('FINDING_BASIS_REQUIRED')
        if target == 'duplicate' and not context.get('canonicalFindingRef'):
            errors.append('CANONICAL_FINDING_REQUIRED')
    if entity == 'action' and target in ('assigned', 'in_progress', 'done') and not context.get('assigneeRef'):
        errors.append('ASSIGNEE_REQUIRED')
    if entity == 'action' and target == 'done':
        if (context.get('basisState') != 'accepted' or not context.get('basisRefs')
                or not context.get('donePredicateMet')):
            errors.append('COMPLETION_BASIS_REQUIRED')
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path)
    parser.add_argument('assessment', type=Path)
    args = parser.parse_args()
    try:
        result = evaluate(load_json(args.bundle), load_json(args.assessment))
    except (OSError, ValueError, RecursionError) as error:
        details = error.errors if isinstance(error, AssessmentError) else [{'code': 'E_INPUT', 'message': 'Cannot read input JSON'}]
        print(json.dumps({'processingStatus': 'input_error', 'errors': details}, indent=2))
        return 2
    print(json.dumps(result, indent=2))
    return 0 if result['verification'] == 'complete' else 1


if __name__ == '__main__':
    raise SystemExit(main())
