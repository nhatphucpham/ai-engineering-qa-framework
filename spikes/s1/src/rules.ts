import { type Doc, InputError, dump, numericEqual as eq, subset } from './json.js';
import { assessment1, assessment2, lifecycle, schemaErrors } from './schema.js';
import { validate } from './contract.js';

export function evaluate(bundle: any, a: any): Doc {
  const v2 = a?.assessmentVersion === '2.0.0';
  const errors = [...validate(bundle), ...schemaErrors(v2 ? assessment2 : assessment1, a, 'E_ASSESSMENT_SCHEMA')];
  if (errors.length) throw new InputError(errors);
  const invalid = (code: string) => errors.push({ code, message: 'Assessment consistency check failed' });
  const project = bundle.projects.find((p: Doc) => p.id === a.projectId);
  const h = bundle.handoffs.find((v: Doc) => v.id === a.handoffId);
  if (!project || !h || h.projectId !== project.id) throw new InputError([{ code: 'E_ASSESSMENT_REFERENCE' }]);
  if (a.candidateRevision !== h.candidateRevision || !eq(a.projectConfigVersion, project.configVersion) || !eq(a.dataPolicyVersion, project.dataPolicy.version)) invalid('E_ASSESSMENT_VERSION');
  const artifacts = new Map<string, Doc>(bundle.artifacts.map((v: Doc) => [v.id, v]));
  const artifactOk = (id: string) => { const v = artifacts.get(id); return v && v.projectId === project.id && (v.taskRef === null || v.taskRef === h.taskRef); };
  if (!artifactOk(a.policySourceArtifactId)) invalid('E_ASSESSMENT_REFERENCE');
  const criteria = new Map<string, Doc>(h.criteria.map((c: Doc) => [c.id, c]));
  const plans = new Map<string, Doc>(a.criteria.map((p: Doc) => [p.criterionId, p]));
  if (plans.size !== a.criteria.length || !subset(plans.keys(), criteria.keys()) || !subset(criteria.keys(), plans.keys())) invalid('E_ASSESSMENT_COVERAGE');
  for (const plan of a.criteria) {
    if (new Set(plan.obligations.map((o: Doc) => o.id)).size !== plan.obligations.length) invalid('E_ASSESSMENT_REFERENCE');
    if (plan.obligations.some((o: Doc) => !artifactOk(o.sourceArtifactId))) invalid('E_ASSESSMENT_REFERENCE');
    const contexts = new Map<string, Doc>(plan.comparisonContexts.map((c: Doc) => [c.id, c]));
    if (contexts.size !== plan.comparisonContexts.length) invalid('E_ASSESSMENT_CONTEXT');
    if (plan.comparisonContexts.some((c: Doc) => !artifactOk(c.sourceArtifactId))) invalid('E_ASSESSMENT_REFERENCE');
    if (plan.obligations.some((o: Doc) => !subset(o.requiredComparisonKeys, contexts.keys()))) invalid('E_ASSESSMENT_CONTEXT');
    const na = plan.naDecision;
    if (plan.applicability === 'applicable' && na !== null) invalid('E_ASSESSMENT_APPLICABILITY');
    if (na?.sourceArtifactId && !artifactOk(na.sourceArtifactId)) invalid('E_ASSESSMENT_REFERENCE');
  }
  const evidence = new Map<string, Doc>(bundle.evidence.filter((e: Doc) => e.projectId === project.id && e.handoffId === h.id).map((e: Doc) => [e.id, e]));
  const reviews = new Map<string, Doc>(a.evidenceReviews.map((r: Doc) => [r.evidenceId, r]));
  if (reviews.size !== a.evidenceReviews.length || !subset(reviews.keys(), evidence.keys())) invalid('E_ASSESSMENT_REFERENCE');
  const bindingKeys: string[] = [];
  for (const b of a.bindings) {
    const plan = plans.get(b.criterionId), e = evidence.get(b.evidenceId);
    if (!plan || !e || !e.criterionIds.includes(b.criterionId) || !plan.obligations.some((o: Doc) => o.id === b.obligationId)) invalid('E_ASSESSMENT_REFERENCE');
    else if (b.relation === 'supports' && !plan.obligations.find((o: Doc) => o.id === b.obligationId).requiredComparisonKeys.includes(b.comparisonKey)) invalid('E_ASSESSMENT_REFERENCE');
    if (plan && !plan.comparisonContexts.some((c: Doc) => c.id === b.comparisonKey)) invalid('E_ASSESSMENT_CONTEXT');
    bindingKeys.push(dump([b.criterionId, b.obligationId, b.evidenceId, b.comparisonKey]));
  }
  if (new Set(bindingKeys).size !== bindingKeys.length) invalid('E_ASSESSMENT_BINDING');
  const constraints = new Map<string, Doc>(h.constraints.map((c: Doc) => [c.id, c]));
  const constraintReviews = new Map<string, Doc>(a.constraintReviews.map((r: Doc) => [r.constraintId, r]));
  if (constraintReviews.size !== a.constraintReviews.length || !subset(constraintReviews.keys(), constraints.keys())) invalid('E_ASSESSMENT_REFERENCE');
  for (const review of a.constraintReviews) if (review.sourceArtifactId && !artifactOk(review.sourceArtifactId)) invalid('E_ASSESSMENT_REFERENCE');
  if (errors.length) throw new InputError(errors);

  const recordMode = a.evaluationMode === 'record_review', results: Doc[] = [];
  const level = (e: Doc) => v2 && e.provenance.kind === 'source_reasoning' ? 'source_review' : e.level;
  for (const [cid, criterion] of criteria) {
    const plan = plans.get(cid)!, reasons = new Set<string>(), decisive = new Set<string>(), context = new Set<string>();
    const supports = new Map<string, Doc[]>(), violates = new Map<string, Doc[]>();
    for (const b of a.bindings.filter((b: Doc) => b.criterionId === cid)) {
      const e = evidence.get(b.evidenceId)!, r = reviews.get(e.id);
      let reason: string | undefined;
      if (b.judgment !== 'accepted') reason = b.judgment === 'candidate' ? 'JUDGMENT_PENDING' : 'JUDGMENT_DISPUTED';
      else if (e.revision !== h.candidateRevision) reason = 'STALE_EVIDENCE';
      else if (!r) reason = 'EVIDENCE_REVIEW_MISSING';
      else if (r.integrity !== 'matched') reason = 'INTEGRITY_UNRESOLVED';
      else if (r.attribution !== 'accepted') reason = 'ATTRIBUTION_UNRESOLVED';
      else if (r.scope !== 'accepted') reason = 'SCOPE_UNRESOLVED';
      else if (!plan.allowedProvenance.includes(e.provenance.kind)) reason = 'PROVENANCE_NOT_ALLOWED';
      else if (!recordMode && !['execution', 'source_reasoning'].includes(e.provenance.kind)) reason = 'RECORD_IS_NOT_EXECUTION';
      else if (!['pass', 'fail'].includes(e.outcome)) reason = 'OUTCOME_' + e.outcome.toUpperCase();
      else if (b.relation === 'inconclusive') reason = 'INCONCLUSIVE_BINDING';
      else if ((b.relation === 'supports') !== (e.outcome === 'pass')) reason = 'OUTCOME_RELATION_MISMATCH';
      if (reason) { reasons.add(reason); context.add(e.id); continue; }
      decisive.add(e.id);
      const destination = b.relation === 'supports' ? supports : violates, key = dump([b.obligationId, b.comparisonKey]);
      destination.set(key, [...(destination.get(key) ?? []), e]);
    }
    const conflicts = new Set(Array.from(violates.keys()).filter(k => supports.has(k)));
    const clearViolations = Array.from(violates.keys()).filter(k => !conflicts.has(k));
    let missing = false, openChecks = false;
    for (const obligation of plan.obligations) for (const key of obligation.requiredComparisonKeys) {
      const pair = dump([obligation.id, key]), matches = supports.get(pair) ?? [], checked = [...matches, ...(violates.get(pair) ?? [])];
      if (!matches.length || !subset(plan.requiredLevels, matches.map(level))) missing = true;
      if (!checked.length || !subset(plan.requiredLevels, checked.map(level))) openChecks = true;
    }
    const planPending = plan.planState !== 'accepted' || a.risk.state !== 'accepted' || a.risk.tier === 'unknown';
    let openParts = Boolean(openChecks || conflicts.size || planPending);
    if (v2 && conflicts.size) reasons.add('EVIDENCE_CONFLICT');
    if (planPending) reasons.add('COVERAGE_PLAN_PENDING');
    const na = plan.naDecision, bound = Boolean(na && na.actorRef && na.sourceArtifactId && na.candidateRevision === h.candidateRevision);
    const rejectedNa = plan.applicability === 'not_applicable_requested' && bound && na.state === 'rejected';
    if (rejectedNa) reasons.add('NA_REJECTED_CHECK_AS_APPLICABLE');
    let status: string;
    if (criterion.clarification !== 'clear') { status = 'unverified'; reasons.add('REQUIREMENT_' + criterion.clarification.toUpperCase()); }
    else if (plan.applicability === 'not_applicable_requested' && !rejectedNa) {
      const acceptedNa = bound && na.state === 'accepted';
      if (acceptedNa && !clearViolations.length && !conflicts.size) { status = 'not_applicable'; openParts = false; reasons.add('NA_ACCEPTED'); }
      else { status = 'unverified'; reasons.add(acceptedNa ? 'NA_CONTRADICTED' : 'NA_PENDING'); }
    } else if (clearViolations.length) { status = 'failed'; reasons.add('CURRENT_BEHAVIOR_VIOLATION'); }
    else if (conflicts.size) { status = 'unverified'; reasons.add('EVIDENCE_CONFLICT'); }
    else if (planPending) { status = 'unverified'; reasons.add('COVERAGE_PLAN_PENDING'); }
    else if (missing) { status = 'unverified'; reasons.add('REQUIRED_COVERAGE_MISSING'); }
    else { status = 'verified'; openParts = false; reasons.add('SCOPED_COVERAGE_SATISFIED'); }
    if (recordMode) reasons.add('RECORD_SCOPE_ONLY');
    for (const id of decisive) context.delete(id);
    results.push({ criterionId: cid, status, reasonCodes: Array.from(reasons).sort(), evidenceIds: Array.from(decisive).sort(),
      contextEvidenceIds: Array.from(context).sort(), hasOpenCoverage: openParts, scopeDescription: plan.scopeDescription });
  }
  const constraintResults = h.constraints.map((c: Doc) => {
    const r = constraintReviews.get(c.id), bound = r && r.judgment === 'accepted' && r.actorRef && r.sourceArtifactId === c.sourceArtifactId && r.candidateRevision === h.candidateRevision;
    const status = c.state !== 'pending' && bound ? c.state : 'pending';
    return { constraintId: c.id, status, reasonCode: status !== 'pending' ? 'CONSTRAINT_REVIEW_ACCEPTED' : 'CONSTRAINT_PENDING' };
  });
  const pending = constraintResults.filter((c: Doc) => c.status === 'pending' && constraints.get(c.constraintId)!.mandatory).map((c: Doc) => c.constraintId);
  const unverified = results.some(r => criteria.get(r.criterionId)!.mandatory && r.status === 'unverified');
  const open = results.some(r => criteria.get(r.criterionId)!.mandatory && r.hasOpenCoverage), failed = results.some(r => r.status === 'failed');
  return { rulesVersion: v2 ? 'p2-rules-2.0.0' : 'p2-rules-1.0.0', processingStatus: 'evaluated', evaluationMode: a.evaluationMode,
    statusScope: recordMode ? 'record_only' : 'candidate_scoped_assessment', verification: failed ? 'failed' : unverified || pending.length ? 'incomplete' : 'complete',
    hasUnverifiedMandatory: unverified, hasOpenMandatoryCoverage: open, pendingConstraintIds: pending, criteria: results,
    constraints: constraintResults, humanDecision: 'pending', limitations: [
      'Offline reference semantics over supplied assessment judgments, not authenticated trust or domain truth.',
      'No test execution, model calls, auth, report persistence or runtime enforcement performed.'] };
}

export function validateTransition(entity: string, current: string, target: string, c: any): string[] {
  if (schemaErrors(lifecycle, c, 'unused').length) return ['TRANSITION_CONTEXT_INVALID'];
  const finding: Record<string, string[]> = { candidate: ['confirmed', 'rejected', 'duplicate', 'disputed'], pending: ['confirmed', 'rejected', 'duplicate', 'disputed'],
    disputed: ['confirmed', 'rejected', 'duplicate'], confirmed: ['disputed'], rejected: ['disputed'], duplicate: ['disputed'] };
  const action: Record<string, string[]> = { proposed: ['assigned', 'blocked'], assigned: ['in_progress', 'blocked'], in_progress: ['done', 'blocked'], blocked: ['assigned', 'in_progress'], done: ['assigned'] };
  const table = entity === 'finding' ? finding : entity === 'action' ? action : {}, errors: string[] = [];
  if (!Object.hasOwn(table, current) || !table[current].includes(target)) errors.push('TRANSITION_NOT_ALLOWED');
  if (!c.authorized) errors.push('ACTOR_NOT_AUTHORIZED');
  if (!c.rationale) errors.push('RATIONALE_REQUIRED');
  if (entity === 'finding' && ['confirmed', 'rejected', 'duplicate'].includes(target)) {
    if (c.basisState !== 'accepted' || !c.basisRefs?.length) errors.push('FINDING_BASIS_REQUIRED');
    if (target === 'duplicate' && !c.canonicalFindingRef) errors.push('CANONICAL_FINDING_REQUIRED');
  }
  if (entity === 'action' && ['assigned', 'in_progress', 'done'].includes(target) && !c.assigneeRef) errors.push('ASSIGNEE_REQUIRED');
  if (entity === 'action' && target === 'done' && (c.basisState !== 'accepted' || !c.basisRefs?.length || !c.donePredicateMet)) errors.push('COMPLETION_BASIS_REQUIRED');
  return errors;
}
