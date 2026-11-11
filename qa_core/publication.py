"""Staged internal publication/replay package; no durable storage or export authority."""

import copy
import json

from jsonschema import Draft202012Validator
from referencing import Resource

from .contracts import FORMATS, ROOT, SCHEMA as BUNDLE_SCHEMA
from .reports import digest
from .rules import AssessmentError, SCHEMA_V2 as ASSESSMENT_SCHEMA
from .runtime import REGISTRY, SCHEMA as REPORT_SCHEMA, PREPARED_SCHEMA, propose_completion, error


SCHEMA = json.loads((ROOT / 'schemas/qa-publication-package-v1.schema.json').read_text(encoding='utf-8'))
Draft202012Validator.check_schema(SCHEMA)
registry = REGISTRY
for dependency in (BUNDLE_SCHEMA, ASSESSMENT_SCHEMA, REPORT_SCHEMA, PREPARED_SCHEMA):
    registry = registry.with_resource(dependency['$id'], Resource.from_contents(dependency))
VALIDATOR = Draft202012Validator(SCHEMA, registry=registry, format_checker=FORMATS)


def asset_entry(slot, value):
    """Identity is parsed canonical JSON, not original file bytes or source attestation."""
    canonical = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    return {'slot': slot, 'mediaType': 'application/json', 'sha256': digest(value),
            'canonicalByteLength': len(canonical.encode('utf-8'))}


def create_publication_package(bundle, assessment, *, run_id, report_id):
    prepared = propose_completion(bundle, assessment, run_id, report_id)
    run = next(r for r in bundle['runs'] if r['id'] == run_id)
    completed = copy.deepcopy(run)
    completed.update(copy.deepcopy(prepared['completion']['runMutation']))
    report = prepared['report']
    scope = report['content']['scope']
    payloads = copy.deepcopy({'bundle': bundle, 'assessment': assessment, 'prepared': prepared})
    package = {
        'packageVersion': '1.0.0', 'kind': 'internal_publication_candidate',
        'classification': 'synthetic-only', 'publicationState': 'staged',
        'handling': {'storageClass': 'restricted_internal_replay', 'inputScope': 'whole_bundle',
                     'outboundAuthorization': 'not_evaluated', 'artifactBytesIncluded': False},
        'target': {**{key: scope[key] for key in ('projectId', 'taskRef', 'handoffId', 'candidateRevision',
                                                 'requirementVersion', 'projectConfigVersion', 'dataPolicyVersion')},
                   'runId': run_id, 'reportId': report_id},
        # The frozen bundle may include other projects/tasks: never relabel it as target-only.
        'containedScopes': {'projectIds': sorted(p['id'] for p in bundle['projects']),
                            'tasks': sorted(({'projectId': t['projectId'], 'taskRef': t['id']}
                                             for t in bundle['tasks']),
                                            key=lambda item: (item['projectId'], item['taskRef']))},
        'manifest': {'manifestVersion': '1.0.0', 'algorithm': 'sha256-python-json-v1',
                     'entries': [asset_entry(slot, payloads[slot]) for slot in ('bundle', 'assessment', 'prepared')]},
        'payloads': payloads,
        'graph': {'graphVersion': '1.0.0', 'completedRunCandidate': completed,
                  'reportReference': {'projectId': run['projectId'], 'runId': run_id, 'reportId': report_id,
                                      'reportSha256': digest(report)},
                  'reportReadyCandidate': {'projectId': run['projectId'], 'runId': run_id,
                                           **copy.deepcopy(prepared['completion']['eventProposal'])}},
    }
    try:
        if list(VALIDATOR.iter_errors(package)):
            raise AssessmentError(error('E_PUBLICATION_SCHEMA', 'Unsupported internal publication package shape'))
        digest(package)  # Do not return JSON that the harness cannot encode.
    except (TypeError, ValueError, UnicodeError, RecursionError):
        raise AssessmentError(error('E_PUBLICATION_INPUT', 'Cannot package supplied JSON and context')) from None
    return package


def validate_publication_package(package, *, expected_bundle_sha256, expected_assessment_sha256,
                                 run_id, report_id):
    """Replay against caller-held input anchors, never hashes learned from this package.

    This proves deterministic derivation only, not who supplied the anchors,
    authenticated judgments, durable publication or current read/export policy.
    """
    try:
        if list(VALIDATOR.iter_errors(package)):
            return error('E_PUBLICATION_SCHEMA', 'Unsupported internal publication package shape or version')
        payloads = package['payloads']
        if (digest(payloads['bundle']) != expected_bundle_sha256
                or digest(payloads['assessment']) != expected_assessment_sha256):
            return error('E_PUBLICATION_BINDING', 'Package inputs differ from caller-held input digests')
        expected = create_publication_package(payloads['bundle'], payloads['assessment'],
                                               run_id=run_id, report_id=report_id)
        if digest(package) != digest(expected):
            return error('E_PUBLICATION_DERIVATION', 'Package differs from exact manifest/report/run/event derivation')
    except (AssessmentError, TypeError, ValueError, UnicodeError, RecursionError):
        return error('E_PUBLICATION_INPUT', 'Cannot replay package from supplied JSON and context')
    return []
