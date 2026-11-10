import { readFileSync } from 'node:fs';
import { performance } from 'node:perf_hooks';
import { type Doc, InputError, dump, parse } from './json.js';

const boot = performance.now();
const { execute, response } = await import('./dispatch.js');
const importCompileMs = performance.now() - boot;
const read = (path: string) => parse(new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(readFileSync(path)));
const args = process.argv.slice(2);
const output = (value: any) => process.stdout.write(dump(value, true) + '\n');
try {
  if (process.versions.node !== '26.13.0') throw new InputError([{ code: 'E_RUNTIME_VERSION' }]);
  if (args[0] === '--batch') {
    if (args.length !== 2) throw new InputError();
    const requests = read(args[1]), start = performance.now(), cpu = process.cpuUsage();
    if (!Array.isArray(requests)) throw new InputError();
    const results = requests.map(response);
    const usage = process.cpuUsage(cpu);
    output({ results, metrics: { runtime: process.versions.node, lts: process.release.lts ?? null, platform: process.platform, arch: process.arch,
      importCompileMs, warmBatchMs: performance.now() - start, warmUserUS: usage.user, warmSystemUS: usage.system,
      peakRSSBytes: process.resourceUsage().maxRSS * 1024, heapUsedBytes: process.memoryUsage().heapUsed, requestCount: requests.length } });
  } else {
    if (!((args[0] === 'contract' && args.length === 2) || (args[0] === 'evaluate' && args.length === 3) ||
      (args[0] === 'report' && (args.length === 3 || (args.length === 5 && args[3] === '--check'))))) throw new InputError();
    const op = args[0], request: Doc = { op, bundle: read(args[1]) };
    if (op !== 'contract') request.assessment = read(args[2]);
    if (op === 'report' && args[3] === '--check') { request.op = 'check'; request.report = read(args[4]); }
    const result = execute(request);
    if (request.op === 'check') { output({ processingStatus: result.length ? 'input_error' : 'report_validated', valid: !result.length, errors: result.map((code: string) => ({ code })) }); process.exitCode = result.length ? 2 : 0; }
    else if (op === 'contract') { output({ valid: result.valid, errors: result.codes.map((code: string) => ({ code })) }); process.exitCode = result.valid ? 0 : 1; }
    else { output(result); process.exitCode = (op === 'report' ? result.assessment.verification : result.verification) === 'complete' ? 0 : 1; }
  }
} catch (error) {
  // Same safe machine-level error boundary, no file paths or raw input echoed.
  const errors = args[0] === 'evaluate' && error instanceof InputError ? error.issues.map(e => ({ code: e.code })) :
    [{ code: 'E_INPUT', message: 'Cannot derive output from supplied JSON' }];
  output(args[0] === 'contract' ? { valid: false, errors: [{ code: 'E_INPUT', message: 'Cannot read UTF-8 JSON input' }] } :
    { processingStatus: 'input_error', errors });
  process.exitCode = 2;
}
