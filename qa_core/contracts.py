"""Offline P1 specimen validation, not the QA engine or a security boundary."""

from datetime import datetime
import json
from pathlib import Path, PurePosixPath

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / 'schemas/qa-contract-v2.schema.json').read_text(encoding='utf-8'))
Draft202012Validator.check_schema(SCHEMA)
FORMATS = FormatChecker()


@FORMATS.checks('date-time', raises=(ValueError, TypeError))
def utc_timestamp(value):
    # The contract deliberately canonicalizes timestamps to UTC Z, no leap seconds.
    if not isinstance(value, str):
        return True  # type checking remains the schema's responsibility
    if not value.endswith('Z'):
        return False
    parsed = datetime.fromisoformat(value[:-1] + '+00:00')
    return parsed.tzinfo is not None


VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FORMATS)
COLLECTIONS = ('projects', 'tasks', 'artifacts', 'handoffs', 'evidence', 'events', 'commands', 'runs', 'reports')


def validate(bundle):
    errors = []

    def fail(code, path, message):
        errors.append({'code': code, 'path': path, 'message': message})

    if isinstance(bundle, dict) and 'contractVersion' in bundle and bundle['contractVersion'] != '2.0.0':
        fail('E_CONTRACT_VERSION', '/contractVersion', 'Active validator requires contract 2.0.0; legacy versions are archived')
        return errors

    # Avoid echoing arbitrary input, potentially including secret-like values.
    for error in VALIDATOR.iter_errors(bundle):
        path = '/' + '/'.join(str(part) for part in error.absolute_path)
        fail('E_SCHEMA', path, 'Schema constraint failed: ' + str(error.validator))
    if errors:
        return errors

    tables = {}
    for collection in COLLECTIONS:
        table = {}
        for index, item in enumerate(bundle[collection]):
            if item['id'] in table:
                fail('E_DUPLICATE_ID', f'/{collection}/{index}/id', 'Duplicate collection ID')
            table[item['id']] = item
        tables[collection] = table
    if errors:
        return errors

    def lookup(collection, item_id, project_id, path):
        item = tables[collection].get(item_id)
        if item is None:
            fail('E_REFERENCE', path, 'Reference does not exist in this bundle')
        elif collection != 'projects' and item['projectId'] != project_id:
            fail('E_PROJECT_BOUNDARY', path, 'Reference belongs to another project')
            return None
        return item

    for collection in COLLECTIONS[1:]:
        for index, item in enumerate(bundle[collection]):
            lookup('projects', item['projectId'], item['projectId'], f'/{collection}/{index}/projectId')

    def unique(values, path):
        if len(values) != len(set(values)):
            fail('E_DUPLICATE_ID', path, 'Duplicate local ID or reference')

    def reject_cycles(edges, path, code):
        checked = set()
        for start in edges:
            current, trail = start, set()
            while current in edges and current not in checked:
                if current in trail:
                    fail(code, path, 'Reference chain contains a cycle and has no canonical root')
                    break
                trail.add(current)
                current = edges[current]
            checked.update(trail)

    for index, member in enumerate(bundle['memberships']):
        lookup('projects', member['projectId'], member['projectId'], f'/memberships/{index}')
    unique([(m['projectId'], m['principalId']) for m in bundle['memberships']], '/memberships')

    def safe_path(path, at):
        if any(part in ('', '.', '..') for part in path.split('/')) or ':' in path:
            fail('E_PATH', at, 'Only normalized workspace-relative POSIX paths allowed')
        if PurePosixPath(path).is_absolute():
            fail('E_PATH', at, 'Absolute path not allowed')

    for index, artifact in enumerate(bundle['artifacts']):
        safe_path(artifact['relativePath'], f'/artifacts/{index}/relativePath')
        if artifact['taskRef']:
            lookup('tasks', artifact['taskRef'], artifact['projectId'], f'/artifacts/{index}/taskRef')
        if artifact['kind'] in ('source', 'diff', 'test_output', 'qc_record') and not artifact['taskRef']:
            fail('E_TASK_BOUNDARY', f'/artifacts/{index}', 'Candidate-bound artifacts require task identity')
    for index, project in enumerate(bundle['projects']):
        runtime = project['runtime']
        if runtime['mode'] == 'model_api' and runtime['provider'] not in project['dataPolicy']['allowedProviders']:
            fail('E_DATA_POLICY', f'/projects/{index}/runtime', 'Provider is not allowed by project policy')
        for key in ('allowedPaths', 'deniedPaths'):
            for path in project['dataPolicy'][key]:
                safe_path(path, f'/projects/{index}/dataPolicy/{key}')
        unique([c['id'] for c in project['checks']], f'/projects/{index}/checks')
        for check in project['checks']:
            artifact = lookup('artifacts', check['configArtifactId'], project['id'], f'/projects/{index}/checks')
            if artifact and artifact['kind'] != 'check_config':
                fail('E_REFERENCE_TYPE', f'/projects/{index}/checks', 'Check configuration must reference check_config')

    for index, handoff in enumerate(bundle['handoffs']):
        at = f'/handoffs/{index}'
        project = handoff['projectId']
        lookup('tasks', handoff['taskRef'], project, at + '/taskRef')
        unique([c['id'] for c in handoff['criteria']], at + '/criteria')
        unique([c['id'] for c in handoff['constraints']], at + '/constraints')
        stages = [s['stage'] for s in handoff['stageRecords']]
        if sorted(stages) != ['developer_self_test', 'qc']:
            fail('E_STAGE_RECORD', at + '/stageRecords', 'Declare self-test and QC exactly once, even when unknown')
        for criterion in handoff['criteria']:
            for claim in criterion['claims']:
                artifact = lookup('artifacts', claim['artifactId'], project, at + '/criteria/claims')
                if artifact and artifact['taskRef'] not in (None, handoff['taskRef']):
                    fail('E_TASK_BOUNDARY', at + '/criteria/claims', 'Claim source belongs to another task')
        for field, kind in [('sourceArtifactIds', 'source'), ('diffArtifactIds', 'diff')]:
            for aid in handoff[field]:
                artifact = lookup('artifacts', aid, project, at + '/' + field)
                if not artifact:
                    continue
                if artifact['kind'] != kind:
                    fail('E_REFERENCE_TYPE', at + '/' + field, 'Handoff input artifact has the wrong kind')
                if artifact['taskRef'] != handoff['taskRef']:
                    fail('E_TASK_BOUNDARY', at + '/' + field, 'Source/diff belongs to another task')
                if artifact['revision'] != handoff['candidateRevision']:
                    fail('E_SOURCE_REVISION', at + '/' + field, 'Handoff source/diff differs from candidate')
        for source in handoff['constraints'] + handoff['knownIssues']:
            artifact = lookup('artifacts', source['sourceArtifactId'], project, at + '/sourceArtifactId')
            if artifact and artifact['taskRef'] not in (None, handoff['taskRef']):
                fail('E_TASK_BOUNDARY', at + '/sourceArtifactId', 'Constraint/issue source belongs to another task')
        for stage in handoff['stageRecords']:
            if (stage['state'] == 'provided') != bool(stage['evidenceIds']):
                fail('E_STAGE_RECORD', at + '/stageRecords', 'Provided needs evidence; unknown/not_performed has none')
            for eid in stage['evidenceIds']:
                ev = lookup('evidence', eid, project, at + '/stageRecords/evidenceIds')
                if ev and ev['handoffId'] != handoff['id']:
                    fail('E_REFERENCE', at + '/stageRecords', 'Evidence belongs to another handoff')

    for index, ev in enumerate(bundle['evidence']):
        at = f'/evidence/{index}'
        handoff = lookup('handoffs', ev['handoffId'], ev['projectId'], at + '/handoffId')
        artifact = lookup('artifacts', ev['provenance']['sourceArtifactId'], ev['projectId'], at + '/provenance/sourceArtifactId')
        if artifact and artifact['kind'] in ('source', 'diff', 'test_output', 'qc_record') and artifact['revision'] != ev['revision']:
            fail('E_SOURCE_REVISION', at, 'Candidate-bound source revision contradicts evidence revision')
        if handoff:
            if artifact and artifact['taskRef'] not in (None, handoff['taskRef']):
                fail('E_TASK_BOUNDARY', at, 'Evidence source belongs to another task')
            criteria = {c['id'] for c in handoff['criteria']}
            if not set(ev['criterionIds']) <= criteria:
                fail('E_REFERENCE', at + '/criterionIds', 'Criterion is absent from handoff')
        if ev['outcome'] in ('fail', 'error', 'skipped', 'blocked', 'not_run', 'unknown') and not ev['reason']:
            fail('E_OUTCOME_REASON', at, 'Non-pass outcome needs a reason')
        if ev['provenance']['kind'] == 'execution' and (not ev['executionRef'] or not ev['provenance']['observedAt']):
            fail('E_PROVENANCE', at, 'Execution claim requires execution reference and observation time')
        if ev['provenance']['kind'] == 'authored_mock' and ev['executionRef'] is not None:
            fail('E_PROVENANCE', at, 'Authored mock cannot claim an execution reference')

    for index, event in enumerate(bundle['events']):
        parts = [event[k] for k in ('projectId', 'kind', 'subjectRef', 'occurrenceRef', 'candidateRevision')]
        # Components containing the separator must be rejected, not ambiguously joined.
        if any('|' in part for part in parts) or event['normalizedKey'] != '|'.join(parts):
            fail('E_EVENT_KEY', f'/events/{index}', 'Normalized identity excludes delivery/transport and includes occurrence')
        if event['kind'] == 'pr_ready' and event['ingress'] == 'internal':
            fail('E_EVENT_KEY', f'/events/{index}', 'PR event must use the configured GitHub ingress')
    unique([e['normalizedKey'] for e in bundle['events']], '/events/normalizedKey')

    command_keys = {}

    for index, command in enumerate(bundle['commands']):
        at = f'/commands/{index}'
        body = command['body']
        key = (command['projectId'], command['idempotencyKey'])
        fingerprint = (command['type'], json.dumps(body, sort_keys=True))
        if key in command_keys and command_keys[key] != fingerprint:
            fail('E_IDEMPOTENCY', at, 'Same idempotency key cannot identify a different command body')
        command_keys[key] = fingerprint
        if command['type'] == 'start_run':
            handoff = lookup('handoffs', body['handoffId'], command['projectId'], at)
            project = tables['projects'].get(command['projectId'])
            if handoff and body['candidateRevision'] != handoff['candidateRevision']:
                fail('E_REVISION', at, 'Start revision differs from handoff candidate')
            if project and body['expectedProjectVersion'] != project['configVersion']:
                fail('E_VERSION', at, 'Project version precondition differs')
        else:
            run = lookup('runs', body['runId'], command['projectId'], at)
            if run and body['expectedRunVersion'] != run['stateVersion']:
                fail('E_VERSION', at, 'Run version precondition differs')

    accepted_triggers = set()
    for index, run in enumerate(bundle['runs']):
        at = f'/runs/{index}'
        handoff = lookup('handoffs', run['handoffId'], run['projectId'], at)
        project = tables['projects'].get(run['projectId'])
        if handoff and run['candidateRevision'] != handoff['candidateRevision']:
            fail('E_REVISION', at, 'Run candidate differs from handoff')
        if project and (run['projectConfigVersion'] != project['configVersion'] or run['dataPolicyVersion'] != project['dataPolicy']['version']):
            fail('E_VERSION', at, 'Bundle must contain the exact frozen project/policy snapshot')
        if run['triggerEventId']:
            event = lookup('events', run['triggerEventId'], run['projectId'], at)
            if event and event['candidateRevision'] != run['candidateRevision']:
                fail('E_REVISION', at, 'Trigger candidate differs from run')
            trigger_key = (run['projectId'], run['triggerEventId'])
            if trigger_key in accepted_triggers:
                fail('E_EVENT_RUN_DUPLICATE', at, 'One accepted event may create only one initial run')
            accepted_triggers.add(trigger_key)
        if run['rerunOfRunId']:
            prior = lookup('runs', run['rerunOfRunId'], run['projectId'], at + '/rerunOfRunId')
            if run['triggerEventId']:
                fail('E_EVENT_RUN_DUPLICATE', at, 'Explicit rerun must not consume the initial trigger again')
            if prior and handoff:
                prior_handoff = tables['handoffs'].get(prior['handoffId'])
                if prior_handoff and prior_handoff['taskRef'] != handoff['taskRef']:
                    fail('E_TASK_BOUNDARY', at, 'Rerun lineage belongs to another task')
        if run['state'] in ('completed', 'failed', 'cancelled') and run['lease'] is not None:
            fail('E_LEASE', at, 'Terminal run must not retain an active lease')
        active = run['state'] in ('claimed', 'collecting', 'validating', 'analyzing', 'checking')
        if active and (run['lease'] is None or run['attempt'] < 1):
            fail('E_LEASE', at, 'Active phase needs a claim and positive attempt')
        if run['state'] in ('queued', 'waiting_input', 'waiting_permission') and run['lease'] is not None:
            fail('E_LEASE', at, 'Queued or waiting phase must release worker lease')
        if run['state'] in ('waiting_input', 'waiting_permission') and not run['waitingReasons']:
            fail('E_RUN_STATE', at, 'Waiting state requires an explicit reason')
        if run['state'] == 'completed' and not run['reportId']:
            fail('E_RUN_STATE', at, 'Completed processing requires a report')
        if run['reportId']:
            report = lookup('reports', run['reportId'], run['projectId'], at)
            if report and report['runId'] != run['id']:
                fail('E_REFERENCE', at, 'Report belongs to another run')

    reject_cycles({r['id']: r['rerunOfRunId'] for r in bundle['runs'] if r['rerunOfRunId']}, '/runs/rerunOfRunId', 'E_RERUN_LINEAGE')

    for index, report in enumerate(bundle['reports']):
        at = f'/reports/{index}'
        run = lookup('runs', report['runId'], report['projectId'], at)
        handoff = lookup('handoffs', report['handoffId'], report['projectId'], at)
        if not run or not handoff:
            continue
        if run['handoffId'] != handoff['id'] or run['candidateRevision'] != report['candidateRevision']:
            fail('E_REVISION', at, 'Report run/handoff/candidate mismatch')
        criteria = {c['id']: c for c in handoff['criteria']}
        result_ids = [c['criterionId'] for c in report['criteria']]
        unique(result_ids, at + '/criteria')
        if set(result_ids) != set(criteria):
            fail('E_REFERENCE', at + '/criteria', 'Report must account for every declared criterion')
        unverified = False
        for result in report['criteria']:
            criterion = criteria.get(result['criterionId'])
            if not criterion:
                continue
            unverified |= criterion['mandatory'] and result['status'] == 'unverified'
            if result['status'] in ('verified', 'failed') and result['assessmentKind'] == 'insufficient':
                fail('E_ASSESSMENT', at + '/criteria', 'Insufficient assessment cannot be conclusive')
            if criterion['clarification'] != 'clear' and result['status'] != 'unverified':
                fail('E_CLARIFICATION', at + '/criteria', 'Unresolved requirement cannot receive a conclusive status')
            decisive = []
            unique(result['evidenceIds'] + result['contextEvidenceIds'], at + '/criteria/evidenceIds')
            for eid in result['evidenceIds'] + result['contextEvidenceIds']:
                ev = lookup('evidence', eid, report['projectId'], at + '/criteria/evidenceIds')
                if ev and (ev['handoffId'] != handoff['id'] or result['criterionId'] not in ev['criterionIds']):
                    fail('E_REFERENCE', at + '/criteria', 'Cited evidence does not map to this handoff/criterion')
                if ev and eid in result['evidenceIds']:
                    decisive.append(ev)
                    if result['status'] in ('verified', 'failed') and ev['revision'] != report['candidateRevision']:
                        fail('E_REPORT_STALE', at + '/criteria', 'Conclusive assessment cannot rely on decisive evidence for another revision')
            if result['assessmentKind'] == 'execution_supported' and not any(
                    e['provenance']['kind'] == 'execution' and e['executionRef']
                    and e['provenance']['observedAt'] and e['revision'] == report['candidateRevision']
                    for e in decisive):
                fail('E_ASSESSMENT_PROVENANCE', at + '/criteria', 'Execution-supported requires current execution provenance among decisive evidence')
            if result['assessmentKind'] == 'source_reasoning' and not any(
                    e['provenance']['kind'] == 'source_reasoning' and e['revision'] == report['candidateRevision']
                    for e in decisive):
                fail('E_ASSESSMENT_PROVENANCE', at + '/criteria', 'Source-reasoning assessment requires matching decisive provenance')
            if result['status'] in ('verified', 'failed') and not result['evidenceIds']:
                fail('E_REFERENCE', at + '/criteria', 'Conclusive criterion needs an evidence reference')
        if unverified != report['hasUnverifiedMandatory']:
            fail('E_REPORT_SUMMARY', at, 'Mandatory unverified flag disagrees with criteria')
        pending_constraint = any(c['mandatory'] and c['state'] == 'pending' for c in handoff['constraints'])
        failed = any(c['status'] == 'failed' for c in report['criteria'])
        expected = 'failed' if failed else ('incomplete' if unverified or pending_constraint else 'complete')
        if report['verification'] != expected:
            fail('E_REPORT_SUMMARY', at, 'Summary contradicts declared criterion/constraint states; not an AC sufficiency proof')
        finding_ids = [f['id'] for f in report['findings']]
        unique(finding_ids, at + '/findings')
        unique([a['id'] for a in report['actions']], at + '/actions')
        for finding in report['findings']:
            if not set(finding['criterionIds']) <= set(criteria):
                fail('E_REFERENCE', at + '/findings', 'Finding criterion is not declared')
            for eid in finding['evidenceIds']:
                ev = lookup('evidence', eid, report['projectId'], at + '/findings/evidenceIds')
                if ev and ev['handoffId'] != handoff['id']:
                    fail('E_REFERENCE', at + '/findings/evidenceIds', 'Finding evidence belongs to another handoff')
            duplicate = finding['duplicateOf']
            if (finding['verdict'] == 'duplicate') != bool(duplicate) or (duplicate and (duplicate not in finding_ids or duplicate == finding['id'])):
                fail('E_DUPLICATE_FINDING', at + '/findings', 'Duplicate must reference another finding in this report')
        for action in report['actions']:
            if not set(action['findingIds']) <= set(finding_ids):
                fail('E_REFERENCE', at + '/actions', 'Action finding is absent from report')
            if action['state'] == 'done' and action['assigneeRef'] is None:
                fail('E_ACTION_STATE', at + '/actions', 'Done requires a named assignee; completion proof still belongs to P2/runtime')
        reject_cycles({f['id']: f['duplicateOf'] for f in report['findings'] if f['duplicateOf']}, at + '/findings', 'E_DUPLICATE_FINDING')

    unique([r['id'] for r in bundle['workerResults']], '/workerResults')
    for index, result in enumerate(bundle['workerResults']):
        at = f'/workerResults/{index}'
        run = lookup('runs', result['runId'], result['projectId'], at)
        if not run:
            continue
        lease = run['lease']
        if (not lease or run['state'] not in ('claimed', 'collecting', 'validating', 'analyzing', 'checking')
                or result['attempt'] != run['attempt']
                or result['fencingToken'] != lease['fencingToken']
                or result['observedRunVersion'] != run['stateVersion']):
            fail('E_FENCING', at, 'Result does not match current active attempt/lease/version')
        if result['candidateRevision'] != run['candidateRevision']:
            fail('E_REVISION', at, 'Worker result candidate differs from run')
        for eid in result['evidenceIds']:
            ev = lookup('evidence', eid, result['projectId'], at)
            if ev and ev['handoffId'] != run['handoffId']:
                fail('E_REFERENCE', at, 'Worker evidence belongs to another handoff')
            if ev and ev['revision'] != run['candidateRevision']:
                fail('E_REVISION', at, 'New worker evidence must identify this attempt candidate')

    unique([p['id'] for p in bundle['progress']], '/progress')
    unique([(p['runId'], p['sequence']) for p in bundle['progress']], '/progress/sequence')
    for index, event in enumerate(bundle['progress']):
        run = lookup('runs', event['runId'], event['projectId'], f'/progress/{index}')
        if run and event['runStateVersion'] > run['stateVersion']:
            fail('E_VERSION', f'/progress/{index}', 'Progress refers to a future run version')
        if event['type'] == 'run_state' and event['referenceIds']:
            fail('E_REFERENCE_TYPE', f'/progress/{index}', 'Run-state progress uses the runId, no extra references')
        if event['type'] in ('check_completed', 'report_ready'):
            collection = 'evidence' if event['type'] == 'check_completed' else 'reports'
            for rid in event['referenceIds']:
                target = lookup(collection, rid, event['projectId'], f'/progress/{index}')
                if target and run and target['handoffId'] != run['handoffId']:
                    fail('E_REFERENCE', f'/progress/{index}', 'Progress reference belongs to another handoff')
                if target and event['type'] == 'report_ready' and target['runId'] != event['runId']:
                    fail('E_PROGRESS_RUN', f'/progress/{index}', 'Report-ready must reference this exact run, not merely its handoff')
    return errors
