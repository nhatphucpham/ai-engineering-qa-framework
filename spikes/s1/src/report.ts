import { type Doc, type Issue, InputError, clone, digest } from './json.js';
import { reportSchema, schemaErrors } from './schema.js';
import { evaluate } from './rules.js';

export function createReport(bundle: any, a: any): Doc {
  if (a?.assessmentVersion !== '2.0.0') throw new InputError([{ code: 'E_REPORT_ASSESSMENT_VERSION' }]);
  let bindings: Doc;
  try { bindings = { algorithm: 'sha256-python-json-v1', bundleSha256: digest(bundle), assessmentSha256: digest(a) }; }
  catch { throw new InputError([{ code: 'E_INPUT_CANONICAL' }]); }
  const result = evaluate(bundle, a), h = bundle.handoffs.find((h: Doc) => h.id === a.handoffId);
  const plans = new Map<string, Doc>(a.criteria.map((p: Doc) => [p.criterionId, p]));
  const reviews = new Map<string, Doc>(a.constraintReviews.map((r: Doc) => [r.constraintId, r]));
  const evidenceReviews = new Map<string, Doc>(a.evidenceReviews.map((r: Doc) => [r.evidenceId, r]));
  const criteria = new Map<string, Doc>(h.criteria.map((c: Doc) => [c.id, c])), actions: Doc[] = [];
  const action = (criterionIds: string[], constraintIds: string[], ownerRole: string, description: string, doneWhen: string) => {
    actions.push({ id: 'action-' + (actions.length + 1), criterionIds, constraintIds, ownerRole, assigneeRef: null, state: 'proposed', description, doneWhen });
  };
  for (const item of result.criteria) {
    const cid = item.criterionId, reasons = new Set<string>(item.reasonCodes), has = (...values: string[]) => values.some(v => reasons.has(v));
    if (item.status === 'failed') action([cid], [], 'developer', 'Review the current counterexample against the requirement.', 'Resolve or dispute the sourced counterexample; provide fresh evidence in a new assessment.');
    if (!['unverified', 'failed'].includes(item.status) || (item.status === 'failed' && !item.hasOpenCoverage)) continue;
    const before = actions.length;
    if (has('REQUIREMENT_AMBIGUOUS', 'REQUIREMENT_CONFLICT')) action([cid], [], criteria.get(cid)!.ownerRole,
      'Resolve the expected behavior using the cited requirement sources.', 'Provide an authorized clarification in a new requirement/handoff snapshot, then re-evaluate.');
    if (has('NA_PENDING', 'NA_CONTRADICTED')) action([cid], [], criteria.get(cid)!.ownerRole,
      'Obtain a sourced applicability decision and address any cited contrary evidence.',
      'Provide an authorized applicability decision with actor/source on the same candidate and re-evaluate; version requirements only if expected behavior changes.');
    if (has('EVIDENCE_CONFLICT')) action([cid], [], 'qa', 'Investigate the contradictory evidence in its comparison context.',
      'Resolve contradictory evidence and account for required levels/contexts on this candidate.');
    if (has('OUTCOME_BLOCKED', 'OUTCOME_ERROR', 'OUTCOME_SKIPPED', 'OUTCOME_NOT_RUN', 'OUTCOME_UNKNOWN')) action([cid], [], 'check-owner',
      'Resolve the recorded check environment, permission or execution precondition.',
      'Resolve the recorded check outcome reason, rerun the approved check on this candidate, and attach eligible evidence before re-evaluation.');
    if (has('COVERAGE_PLAN_PENDING')) action([cid], [], 'coverage-policy-owner', 'Resolve the scoped risk and coverage-plan decision.',
      'Provide an accepted, sourced risk/coverage plan without expanding the run scope, then re-evaluate.');
    const reviewReasons = ['OUTCOME_RELATION_MISMATCH', 'INCONCLUSIVE_BINDING', 'JUDGMENT_PENDING', 'JUDGMENT_DISPUTED',
      'EVIDENCE_REVIEW_MISSING', 'INTEGRITY_UNRESOLVED', 'ATTRIBUTION_UNRESOLVED', 'SCOPE_UNRESOLVED', 'PROVENANCE_NOT_ALLOWED',
      'RECORD_IS_NOT_EXECUTION', 'STALE_EVIDENCE'].filter(v => reasons.has(v)).sort();
    if (reviewReasons.length) action([cid], [], 'qa', 'Review the evidence binding, provenance or acceptance: ' + reviewReasons.join(', '),
      'Resolve the cited mapping/review issue against actual outcomes and current sources; provide an appropriately sourced assessment and re-evaluate.');
    if (actions.length === before) action([cid], [], 'qa', 'Complete the remaining required evidence levels and comparison contexts.',
      'Supply current, appropriately reviewed evidence for every still-unchecked declared level/context; re-evaluate.');
  }
  for (const item of result.constraints) if (item.status === 'pending') {
    const declaration = h.constraints.find((c: Doc) => c.id === item.constraintId);
    const done = declaration.state === 'pending' ? 'Obtain an authorized resolution and a new handoff snapshot with a resolved declaration, plus an accepted review with actor/source/current candidate; re-evaluate.' :
      'Provide an accepted review with actor/source/current candidate, then re-evaluate.';
    action([], [item.constraintId], 'constraint-review-owner', 'Obtain the scoped constraint review; a declared state alone is insufficient.', done);
  }
  const pending = h.constraints.some((c: Doc) => c.mandatory && c.state === 'pending');
  const legacySummary = result.criteria.some((c: Doc) => c.status === 'failed') ? 'failed' : result.hasUnverifiedMandatory || pending ? 'incomplete' : 'complete';
  const legacyReasons = ['P1_V2_EXPORT_NOT_IMPLEMENTED']; if (legacySummary !== result.verification) legacyReasons.push('P1_V2_CONSTRAINT_COLLISION');
  const selectedEvidence = bundle.evidence.filter((e: Doc) => e.projectId === h.projectId && e.handoffId === h.id);
  const artifactIds = new Set<string>([a.policySourceArtifactId]);
  for (const c of h.criteria) {
    for (const claim of c.claims) artifactIds.add(claim.artifactId);
    const plan = plans.get(c.id)!;
    for (const source of [...plan.obligations, ...plan.comparisonContexts]) artifactIds.add(source.sourceArtifactId);
    if (plan.naDecision?.sourceArtifactId) artifactIds.add(plan.naDecision.sourceArtifactId);
  }
  for (const e of selectedEvidence) artifactIds.add(e.provenance.sourceArtifactId);
  for (const c of [...h.constraints, ...h.knownIssues]) artifactIds.add(c.sourceArtifactId);
  for (const id of [...h.sourceArtifactIds, ...h.diffArtifactIds]) artifactIds.add(id);
  for (const review of a.constraintReviews) if (review.sourceArtifactId) artifactIds.add(review.sourceArtifactId);
  const scope: Doc = Object.fromEntries(['projectId', 'handoffId', 'candidateRevision', 'projectConfigVersion', 'dataPolicyVersion', 'policySourceArtifactId', 'assessorRef'].map(k => [k, a[k]]));
  Object.assign(scope, { taskRef: h.taskRef, requirementVersion: h.requirementVersion });
  const report = clone({ reportVersion: '1.0.0', classification: 'synthetic-only', processingStatus: 'reference_report', inputBindings: bindings, scope,
    assessment: result, assessmentContext: { risk: a.risk, bindings: a.bindings },
    handoffContext: Object.fromEntries(['intake', 'decisionMoment', 'requestedDecision', 'actors', 'riskRationale', 'stageRecords', 'knownIssues', 'sourceArtifactIds', 'diffArtifactIds'].map(k => [k, h[k]])),
    criterionSources: h.criteria.map((c: Doc) => ({ criterion: c, plan: plans.get(c.id) })),
    constraintSources: h.constraints.map((c: Doc) => ({ declaration: c, review: reviews.get(c.id) ?? null })),
    evidenceSources: selectedEvidence.map((e: Doc) => ({ evidence: e, review: evidenceReviews.get(e.id) ?? null })),
    artifacts: bundle.artifacts.filter((v: Doc) => artifactIds.has(v.id)), actions,
    legacyProjection: { status: 'projection_unsupported', reasonCodes: legacyReasons }, limitations: [
      'Synthetic reference report over supplied judgments; no authenticated authority or domain truth.',
      'No project tests, model/network calls, persistence, P1 export or run lifecycle performed.',
      'Digests identify supplied JSON inputs, not source contents, actor authenticity or trust.',
      'Proposed role labels are routing suggestions; no assignee, approval or action completion asserted.'] });
  if (schemaErrors(reportSchema, report, 'unused').length) throw new InputError([{ code: 'E_REPORT_PROJECTION' }]);
  return report;
}

export function validateReport(report: any, bundle: any, assessment: any): Issue[] {
  if (schemaErrors(reportSchema, report, 'unused').length) return [{ code: 'E_REPORT_SCHEMA' }];
  let expected: Doc;
  try { expected = createReport(bundle, assessment); } catch { return [{ code: 'E_REPORT_INPUT' }]; }
  try { if (digest(report) !== digest(expected)) return [{ code: 'E_REPORT_DERIVATION' }]; }
  catch { return [{ code: 'E_REPORT_DERIVATION' }]; }
  return [];
}
