import { type Doc, type Issue, dump, numericEqual as eq, subset } from './json.js';
import { contractSchema, schemaErrors } from './schema.js';

const COLLECTIONS = ['projects', 'tasks', 'artifacts', 'handoffs', 'evidence', 'events', 'commands', 'runs', 'reports'];
const numericKey = (x: any): any => {
  if (x !== null && typeof x === 'object' && 'value' in x && 'integer' in x) {
    return typeof x.value === 'bigint' || Number.isInteger(x.value) ? ['number', BigInt(x.value).toString()] : ['number', x.value];
  }
  return Array.isArray(x) ? x.map(numericKey) : x;
};
export function validate(bundle: any): Issue[] {
  const errors: Issue[] = [];
  const fail = (code: string, path: string, message = 'Contract consistency check failed') => errors.push({ code, path, message });
  if (bundle && typeof bundle === 'object' && !Array.isArray(bundle) && Object.hasOwn(bundle, 'contractVersion') && bundle.contractVersion !== '2.0.0') {
    fail('E_CONTRACT_VERSION', '/contractVersion'); return errors;
  }
  errors.push(...schemaErrors(contractSchema, bundle, 'E_SCHEMA'));
  if (errors.length) return errors;
  const tables = new Map<string, Map<string, Doc>>();
  for (const collection of COLLECTIONS) {
    const table = new Map<string, Doc>();
    bundle[collection].forEach((item: Doc, index: number) => {
      if (table.has(item.id)) fail('E_DUPLICATE_ID', '/' + collection + '/' + index + '/id');
      table.set(item.id, item);
    });
    tables.set(collection, table);
  }
  if (errors.length) return errors;
  const lookup = (collection: string, id: string, project: string, path: string): Doc | undefined => {
    const item = tables.get(collection)!.get(id);
    if (!item) fail('E_REFERENCE', path);
    else if (collection !== 'projects' && item.projectId !== project) { fail('E_PROJECT_BOUNDARY', path); return undefined; }
    return item;
  };
  const unique = (values: any[], path: string) => {
    if (new Set(values.map(v => dump(numericKey(v)))).size !== values.length) fail('E_DUPLICATE_ID', path);
  };
  const cycles = (edges: Map<string, string>, path: string, code: string) => {
    const checked = new Set<string>();
    for (const start of edges.keys()) {
      let current = start; const trail = new Set<string>();
      while (edges.has(current) && !checked.has(current)) {
        if (trail.has(current)) { fail(code, path); break; }
        trail.add(current); current = edges.get(current)!;
      }
      for (const v of trail) checked.add(v);
    }
  };
  for (const collection of COLLECTIONS.slice(1)) bundle[collection].forEach((item: Doc, i: number) => lookup('projects', item.projectId, item.projectId, `/${collection}/${i}/projectId`));
  bundle.memberships.forEach((m: Doc, i: number) => lookup('projects', m.projectId, m.projectId, `/memberships/${i}`));
  unique(bundle.memberships.map((m: Doc) => [m.projectId, m.principalId]), '/memberships');
  const safePath = (value: string, path: string) => {
    if (value.split('/').some(v => ['', '.', '..'].includes(v)) || value.includes(':')) fail('E_PATH', path);
    if (value.startsWith('/')) fail('E_PATH', path);
  };
  bundle.artifacts.forEach((a: Doc, i: number) => {
    safePath(a.relativePath, `/artifacts/${i}/relativePath`);
    if (a.taskRef) lookup('tasks', a.taskRef, a.projectId, `/artifacts/${i}/taskRef`);
    if (['source', 'diff', 'test_output', 'qc_record'].includes(a.kind) && !a.taskRef) fail('E_TASK_BOUNDARY', `/artifacts/${i}`);
  });
  bundle.projects.forEach((p: Doc, i: number) => {
    if (p.runtime.mode === 'model_api' && !p.dataPolicy.allowedProviders.includes(p.runtime.provider)) fail('E_DATA_POLICY', `/projects/${i}/runtime`);
    for (const key of ['allowedPaths', 'deniedPaths']) for (const path of p.dataPolicy[key]) safePath(path, `/projects/${i}/dataPolicy/${key}`);
    unique(p.checks.map((c: Doc) => c.id), `/projects/${i}/checks`);
    for (const check of p.checks) {
      const a = lookup('artifacts', check.configArtifactId, p.id, `/projects/${i}/checks`);
      if (a && a.kind !== 'check_config') fail('E_REFERENCE_TYPE', `/projects/${i}/checks`);
    }
  });
  bundle.handoffs.forEach((h: Doc, i: number) => {
    const at = `/handoffs/${i}`, project = h.projectId;
    lookup('tasks', h.taskRef, project, at + '/taskRef');
    unique(h.criteria.map((c: Doc) => c.id), at + '/criteria'); unique(h.constraints.map((c: Doc) => c.id), at + '/constraints');
    if (dump(h.stageRecords.map((s: Doc) => s.stage).sort()) !== dump(['developer_self_test', 'qc'])) fail('E_STAGE_RECORD', at + '/stageRecords');
    for (const c of h.criteria) for (const claim of c.claims) {
      const a = lookup('artifacts', claim.artifactId, project, at + '/criteria/claims');
      if (a && a.taskRef !== null && a.taskRef !== h.taskRef) fail('E_TASK_BOUNDARY', at + '/criteria/claims');
    }
    for (const [field, kind] of [['sourceArtifactIds', 'source'], ['diffArtifactIds', 'diff']]) for (const id of h[field]) {
      const a = lookup('artifacts', id, project, at + '/' + field);
      if (!a) continue;
      if (a.kind !== kind) fail('E_REFERENCE_TYPE', at + '/' + field);
      if (a.taskRef !== h.taskRef) fail('E_TASK_BOUNDARY', at + '/' + field);
      if (a.revision !== h.candidateRevision) fail('E_SOURCE_REVISION', at + '/' + field);
    }
    for (const source of [...h.constraints, ...h.knownIssues]) {
      const a = lookup('artifacts', source.sourceArtifactId, project, at + '/sourceArtifactId');
      if (a && a.taskRef !== null && a.taskRef !== h.taskRef) fail('E_TASK_BOUNDARY', at + '/sourceArtifactId');
    }
    for (const stage of h.stageRecords) {
      if ((stage.state === 'provided') !== Boolean(stage.evidenceIds.length)) fail('E_STAGE_RECORD', at + '/stageRecords');
      for (const id of stage.evidenceIds) { const e = lookup('evidence', id, project, at + '/stageRecords/evidenceIds'); if (e && e.handoffId !== h.id) fail('E_REFERENCE', at + '/stageRecords'); }
    }
  });
  bundle.evidence.forEach((e: Doc, i: number) => {
    const at = `/evidence/${i}`, h = lookup('handoffs', e.handoffId, e.projectId, at + '/handoffId');
    const a = lookup('artifacts', e.provenance.sourceArtifactId, e.projectId, at + '/provenance/sourceArtifactId');
    if (a && ['source', 'diff', 'test_output', 'qc_record'].includes(a.kind) && a.revision !== e.revision) fail('E_SOURCE_REVISION', at);
    if (h) {
      if (a && a.taskRef !== null && a.taskRef !== h.taskRef) fail('E_TASK_BOUNDARY', at);
      if (!subset(e.criterionIds, h.criteria.map((c: Doc) => c.id))) fail('E_REFERENCE', at + '/criterionIds');
    }
    if (['fail', 'error', 'skipped', 'blocked', 'not_run', 'unknown'].includes(e.outcome) && !e.reason) fail('E_OUTCOME_REASON', at);
    if (e.provenance.kind === 'execution' && (!e.executionRef || !e.provenance.observedAt)) fail('E_PROVENANCE', at);
    if (e.provenance.kind === 'authored_mock' && e.executionRef !== null) fail('E_PROVENANCE', at);
  });
  bundle.events.forEach((e: Doc, i: number) => {
    const parts = ['projectId', 'kind', 'subjectRef', 'occurrenceRef', 'candidateRevision'].map(k => e[k]);
    if (parts.some(p => p.includes('|')) || e.normalizedKey !== parts.join('|')) fail('E_EVENT_KEY', `/events/${i}`);
    if (e.kind === 'pr_ready' && e.ingress === 'internal') fail('E_EVENT_KEY', `/events/${i}`);
  });
  unique(bundle.events.map((e: Doc) => e.normalizedKey), '/events/normalizedKey');
  const commandKeys = new Map<string, string>();
  bundle.commands.forEach((c: Doc, i: number) => {
    const at = `/commands/${i}`, body = c.body, key = dump([c.projectId, c.idempotencyKey]), fingerprint = dump([c.type, body]);
    if (commandKeys.has(key) && commandKeys.get(key) !== fingerprint) fail('E_IDEMPOTENCY', at);
    commandKeys.set(key, fingerprint);
    if (c.type === 'start_run') {
      const h = lookup('handoffs', body.handoffId, c.projectId, at), p = tables.get('projects')!.get(c.projectId);
      if (h && body.candidateRevision !== h.candidateRevision) fail('E_REVISION', at);
      if (p && !eq(body.expectedProjectVersion, p.configVersion)) fail('E_VERSION', at);
    } else { const run = lookup('runs', body.runId, c.projectId, at); if (run && !eq(body.expectedRunVersion, run.stateVersion)) fail('E_VERSION', at); }
  });
  const triggers = new Set<string>();
  bundle.runs.forEach((r: Doc, i: number) => {
    const at = `/runs/${i}`, h = lookup('handoffs', r.handoffId, r.projectId, at), p = tables.get('projects')!.get(r.projectId);
    if (h && r.candidateRevision !== h.candidateRevision) fail('E_REVISION', at);
    if (p && (!eq(r.projectConfigVersion, p.configVersion) || !eq(r.dataPolicyVersion, p.dataPolicy.version))) fail('E_VERSION', at);
    if (r.triggerEventId) {
      const e = lookup('events', r.triggerEventId, r.projectId, at), key = dump([r.projectId, r.triggerEventId]);
      if (e && e.candidateRevision !== r.candidateRevision) fail('E_REVISION', at);
      if (triggers.has(key)) fail('E_EVENT_RUN_DUPLICATE', at); triggers.add(key);
    }
    if (r.rerunOfRunId) {
      const prior = lookup('runs', r.rerunOfRunId, r.projectId, at + '/rerunOfRunId');
      if (r.triggerEventId) fail('E_EVENT_RUN_DUPLICATE', at);
      if (prior && h) { const priorHandoff = tables.get('handoffs')!.get(prior.handoffId); if (priorHandoff && priorHandoff.taskRef !== h.taskRef) fail('E_TASK_BOUNDARY', at); }
    }
    if (['completed', 'failed', 'cancelled'].includes(r.state) && r.lease !== null) fail('E_LEASE', at);
    const active = ['claimed', 'collecting', 'validating', 'analyzing', 'checking'].includes(r.state);
    if (active && (r.lease === null || r.attempt < 1)) fail('E_LEASE', at);
    if (['queued', 'waiting_input', 'waiting_permission'].includes(r.state) && r.lease !== null) fail('E_LEASE', at);
    if (['waiting_input', 'waiting_permission'].includes(r.state) && !r.waitingReasons.length) fail('E_RUN_STATE', at);
    if (r.state === 'completed' && !r.reportId) fail('E_RUN_STATE', at);
    if (r.reportId) { const report = lookup('reports', r.reportId, r.projectId, at); if (report && report.runId !== r.id) fail('E_REFERENCE', at); }
  });
  cycles(new Map(bundle.runs.filter((r: Doc) => r.rerunOfRunId).map((r: Doc) => [r.id, r.rerunOfRunId])), '/runs/rerunOfRunId', 'E_RERUN_LINEAGE');
  bundle.reports.forEach((r: Doc, i: number) => {
    const at = `/reports/${i}`, run = lookup('runs', r.runId, r.projectId, at), h = lookup('handoffs', r.handoffId, r.projectId, at);
    if (!run || !h) return;
    if (run.handoffId !== h.id || run.candidateRevision !== r.candidateRevision) fail('E_REVISION', at);
    const criteria = new Map<string, Doc>(h.criteria.map((c: Doc) => [c.id, c])), ids = r.criteria.map((c: Doc) => c.criterionId);
    unique(ids, at + '/criteria'); if (!subset(ids, criteria.keys()) || !subset(criteria.keys(), ids)) fail('E_REFERENCE', at + '/criteria');
    let unverified = false;
    for (const result of r.criteria) {
      const c = criteria.get(result.criterionId); if (!c) continue;
      unverified ||= c.mandatory && result.status === 'unverified';
      if (['verified', 'failed'].includes(result.status) && result.assessmentKind === 'insufficient') fail('E_ASSESSMENT', at + '/criteria');
      if (c.clarification !== 'clear' && result.status !== 'unverified') fail('E_CLARIFICATION', at + '/criteria');
      const decisive: Doc[] = []; unique([...result.evidenceIds, ...result.contextEvidenceIds], at + '/criteria/evidenceIds');
      for (const id of [...result.evidenceIds, ...result.contextEvidenceIds]) {
        const e = lookup('evidence', id, r.projectId, at + '/criteria/evidenceIds');
        if (e && (e.handoffId !== h.id || !e.criterionIds.includes(result.criterionId))) fail('E_REFERENCE', at + '/criteria');
        if (e && result.evidenceIds.includes(id)) { decisive.push(e); if (['verified', 'failed'].includes(result.status) && e.revision !== r.candidateRevision) fail('E_REPORT_STALE', at + '/criteria'); }
      }
      if (result.assessmentKind === 'execution_supported' && !decisive.some(e => e.provenance.kind === 'execution' && e.executionRef && e.provenance.observedAt && e.revision === r.candidateRevision)) fail('E_ASSESSMENT_PROVENANCE', at + '/criteria');
      if (result.assessmentKind === 'source_reasoning' && !decisive.some(e => e.provenance.kind === 'source_reasoning' && e.revision === r.candidateRevision)) fail('E_ASSESSMENT_PROVENANCE', at + '/criteria');
      if (['verified', 'failed'].includes(result.status) && !result.evidenceIds.length) fail('E_REFERENCE', at + '/criteria');
    }
    if (unverified !== r.hasUnverifiedMandatory) fail('E_REPORT_SUMMARY', at);
    const pending = h.constraints.some((c: Doc) => c.mandatory && c.state === 'pending'), failed = r.criteria.some((c: Doc) => c.status === 'failed');
    if (r.verification !== (failed ? 'failed' : unverified || pending ? 'incomplete' : 'complete')) fail('E_REPORT_SUMMARY', at);
    const findingIds = r.findings.map((f: Doc) => f.id); unique(findingIds, at + '/findings'); unique(r.actions.map((a: Doc) => a.id), at + '/actions');
    for (const f of r.findings) {
      if (!subset(f.criterionIds, criteria.keys())) fail('E_REFERENCE', at + '/findings');
      for (const id of f.evidenceIds) { const e = lookup('evidence', id, r.projectId, at + '/findings/evidenceIds'); if (e && e.handoffId !== h.id) fail('E_REFERENCE', at + '/findings'); }
      if ((f.verdict === 'duplicate') !== Boolean(f.duplicateOf) || (f.duplicateOf && (!findingIds.includes(f.duplicateOf) || f.duplicateOf === f.id))) fail('E_DUPLICATE_FINDING', at + '/findings');
    }
    for (const a of r.actions) { if (!subset(a.findingIds, findingIds)) fail('E_REFERENCE', at + '/actions'); if (a.state === 'done' && a.assigneeRef === null) fail('E_ACTION_STATE', at + '/actions'); }
    cycles(new Map(r.findings.filter((f: Doc) => f.duplicateOf).map((f: Doc) => [f.id, f.duplicateOf])), at + '/findings', 'E_DUPLICATE_FINDING');
  });
  unique(bundle.workerResults.map((r: Doc) => r.id), '/workerResults');
  bundle.workerResults.forEach((r: Doc, i: number) => {
    const at = `/workerResults/${i}`, run = lookup('runs', r.runId, r.projectId, at); if (!run) return;
    const lease = run.lease;
    if (!lease || !['claimed', 'collecting', 'validating', 'analyzing', 'checking'].includes(run.state) || !eq(r.attempt, run.attempt) || !eq(r.fencingToken, lease.fencingToken) || !eq(r.observedRunVersion, run.stateVersion)) fail('E_FENCING', at);
    if (r.candidateRevision !== run.candidateRevision) fail('E_REVISION', at);
    for (const id of r.evidenceIds) { const e = lookup('evidence', id, r.projectId, at); if (e && e.handoffId !== run.handoffId) fail('E_REFERENCE', at); if (e && e.revision !== run.candidateRevision) fail('E_REVISION', at); }
  });
  unique(bundle.progress.map((p: Doc) => p.id), '/progress'); unique(bundle.progress.map((p: Doc) => [p.runId, p.sequence]), '/progress/sequence');
  bundle.progress.forEach((e: Doc, i: number) => {
    const at = `/progress/${i}`, run = lookup('runs', e.runId, e.projectId, at);
    if (run && e.runStateVersion > run.stateVersion) fail('E_VERSION', at);
    if (e.type === 'run_state' && e.referenceIds.length) fail('E_REFERENCE_TYPE', at);
    if (['check_completed', 'report_ready'].includes(e.type)) for (const id of e.referenceIds) {
      const target = lookup(e.type === 'check_completed' ? 'evidence' : 'reports', id, e.projectId, at);
      if (target && run && target.handoffId !== run.handoffId) fail('E_REFERENCE', at);
      if (target && e.type === 'report_ready' && target.runId !== e.runId) fail('E_PROGRESS_RUN', at);
    }
  });
  return errors;
}
