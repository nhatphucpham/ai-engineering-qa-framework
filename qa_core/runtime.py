"""Versioned internal report derivation; supplied snapshots, no persistence or authority."""

import copy
import json

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from .contracts import FORMATS, ROOT
from .reports import SCHEMA as CONTENT_SCHEMA, create_report, digest
from .rules import AssessmentError


SCHEMA = json.loads((ROOT / 'schemas/qa-runtime-report-v1.schema.json').read_text(encoding='utf-8'))
Draft202012Validator.check_schema(SCHEMA)
REGISTRY = Registry().with_resource(CONTENT_SCHEMA['$id'], Resource.from_contents(CONTENT_SCHEMA))
VALIDATOR = Draft202012Validator(SCHEMA, registry=REGISTRY, format_checker=FORMATS)
PREPARED_SCHEMA = json.loads((ROOT / 'schemas/qa-prepared-report-v1.schema.json').read_text(encoding='utf-8'))
Draft202012Validator.check_schema(PREPARED_SCHEMA)
PREPARED_VALIDATOR = Draft202012Validator(
    PREPARED_SCHEMA, registry=REGISTRY.with_resource(SCHEMA['$id'], Resource.from_contents(SCHEMA)),
    format_checker=FORMATS)


def error(code, message):
    return [{'code': code, 'message': message}]


def create_runtime_report(bundle, assessment, run_id, report_id):
    """Bind an assessment-authoritative report to one exact pre-completion run snapshot."""
    content = create_report(bundle, assessment)  # Validates frozen P1 v2 and P2 v2 first.
    run = next((r for r in bundle['runs'] if r['id'] == run_id), None)
    if (run is None or any(run[key] != content['scope'][key] for key in
                          ('projectId', 'handoffId', 'candidateRevision',
                           'projectConfigVersion', 'dataPolicyVersion'))):
        raise AssessmentError(error('E_RUNTIME_RUN', 'Report must identify this exact scoped run'))
    already_reported = (any(r['runId'] == run_id for r in bundle['reports'])
                        or any(p['runId'] == run_id and p['type'] == 'report_ready'
                               for p in bundle['progress']))
    if run['state'] not in ('analyzing', 'checking') or run['reportId'] is not None or already_reported:
        raise AssessmentError(error('E_RUNTIME_PHASE', 'Only an unpublished analyzing/checking run can complete'))
    if any(r['id'] == report_id for r in bundle['reports']):
        raise AssessmentError(error('E_RUNTIME_ID', 'Report identity already exists in the supplied snapshot'))
    report = {
        'runtimeReportVersion': '1.0.0', 'id': report_id,
        'kind': 'internal_assessment_report', 'publicationState': 'proposed',
        'runBinding': {key: run[key] for key in
                       ('id', 'projectId', 'handoffId', 'candidateRevision',
                        'projectConfigVersion', 'dataPolicyVersion', 'stateVersion', 'attempt')},
        'runSnapshotSha256': digest(run), 'content': content,
    }
    if list(VALIDATOR.iter_errors(report)):
        raise AssessmentError(error('E_RUNTIME_SCHEMA', 'Unsupported internal report shape or identity'))
    return copy.deepcopy(report)


def validate_runtime_report(report, bundle, assessment, run_id, report_id):
    """Expected identities are caller context, never inferred from untrusted report fields."""
    if list(VALIDATOR.iter_errors(report)):
        return error('E_RUNTIME_SCHEMA', 'Unsupported internal report shape or version')
    try:
        expected = create_runtime_report(bundle, assessment, run_id, report_id)
        if digest(report) != digest(expected):
            return error('E_RUNTIME_DERIVATION', 'Report differs from exact run/input/rule derivation')
    except (AssessmentError, TypeError, ValueError, UnicodeError, RecursionError):
        return error('E_RUNTIME_INPUT', 'Cannot derive internal report from supplied context')
    return []


def propose_completion(bundle, assessment, run_id, report_id):
    """Return detached atomic-write intent, including incomplete/failed verification.

    This is neither a P1 v2 bundle nor an emitted report_ready event. A future
    application must recheck authority, lease, live policy, CAS and durable refs.
    """
    report = create_runtime_report(bundle, assessment, run_id, report_id)
    run = next(r for r in bundle['runs'] if r['id'] == run_id)
    # JSON Schema integer includes integral floats. Convert before arithmetic so
    # 2**53 + 1 does not round back to 2**53; raw values remain bound by digests.
    next_version = int(run['stateVersion']) + 1
    sequence = max((int(p['sequence']) for p in bundle['progress'] if p['runId'] == run_id), default=0) + 1
    proposal = {
        'completionVersion': '1.0.0', 'kind': 'internal_completion_proposal',
        'projectId': run['projectId'], 'runId': run_id,
        'expectedRunVersion': int(run['stateVersion']), 'expectedAttempt': int(run['attempt']),
        'expectedRunSha256': digest(run), 'reportSha256': digest(report),
        'runMutation': {'state': 'completed', 'stateVersion': next_version,
                        'lease': None, 'reportId': report_id, 'waitingReasons': [], 'terminalReason': None},
        'eventProposal': {'type': 'report_ready', 'sequence': sequence,
                          'runStateVersion': next_version, 'referenceIds': [report_id]},
    }
    prepared = {'report': report, 'completion': proposal}
    try:
        digest(prepared)  # Also reject a successor beyond the JSON encoder limit.
    except (TypeError, ValueError, UnicodeError, RecursionError):
        raise AssessmentError(error('E_COMPLETION_JSON', 'Completion cannot be represented as supported JSON')) from None
    return prepared


def validate_completion(proposal, bundle, assessment, run_id, report_id):
    """Pure graph/derivation check only; never implies a successful transaction."""
    if list(PREPARED_VALIDATOR.iter_errors(proposal)):
        return error('E_COMPLETION_SCHEMA', 'Unsupported prepared report shape or version')
    try:
        expected = propose_completion(bundle, assessment, run_id, report_id)
        if digest(proposal) != digest(expected):
            return error('E_COMPLETION_DERIVATION', 'Completion differs from bound report/run/event intent')
    except (AssessmentError, TypeError, ValueError, UnicodeError, RecursionError):
        return error('E_COMPLETION_INPUT', 'Cannot propose completion from supplied context')
    return []
