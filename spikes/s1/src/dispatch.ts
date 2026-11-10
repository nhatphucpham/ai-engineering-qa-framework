import { type Doc, InputError, clone, digest, dump, parse } from './json.js';
import { validate } from './contract.js';
import { evaluate, validateTransition } from './rules.js';
import { createReport, validateReport } from './report.js';

export function execute(request: Doc): any {
  switch (request.op) {
    case 'contract': { const errors = validate(request.bundle); return { valid: !errors.length, codes: [...new Set(errors.map(e => e.code))].sort() }; }
    case 'evaluate': return evaluate(request.bundle, request.assessment);
    case 'report': return createReport(request.bundle, request.assessment);
    case 'check': return validateReport(request.report, request.bundle, request.assessment).map(e => e.code).sort();
    case 'transition': return validateTransition(request.entity, request.current, request.target, request.context);
    case 'digest': return digest(parse(request.raw));
    case 'detachment': {
      const report = createReport(request.bundle, request.assessment), before = dump([request.bundle, request.assessment]);
      report.criterionSources[0].criterion.expected = 'modified output';
      report.assessmentContext.bindings[0].rationale = 'modified output';
      return before === dump([request.bundle, request.assessment]);
    }
    default: throw new InputError();
  }
}
export function response(request: Doc): Doc {
  const before = dump(request), secondInput = clone(request);
  const run = (input: Doc): Doc => {
    try { return { kind: 'ok', value: execute(input) }; }
    catch (error) { return { kind: 'input_error', codes: error instanceof InputError ? [...new Set(error.issues.map(e => e.code))].sort() : ['E_INTERNAL'] }; }
  };
  const first = run(request), second = run(secondInput);
  return { id: request.id, ...first, noMutation: before === dump(request) && before === dump(secondInput), repeatable: dump(first) === dump(second) };
}
