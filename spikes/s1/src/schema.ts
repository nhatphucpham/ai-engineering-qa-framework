import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import Ajv2020 from 'ajv/dist/2020.js';
import type { ValidateFunction } from 'ajv';
import { type Issue, schemaValue } from './json.js';

export const ROOT = fileURLToPath(new URL('../../../', import.meta.url));
const ajv = new (Ajv2020 as any)({ allErrors: true, strict: true, strictTypes: false,
  strictRequired: false, coerceTypes: false, useDefaults: false, removeAdditional: false });
ajv.addFormat('date-time', (value: string) => {
  const match = /^(\d{4})-(\d\d)-(\d\d)T(\d\d):(\d\d):(\d\d)(?:\.\d+)?Z$/.exec(value);
  if (!match) return false;
  const [year, month, day, hour, minute, second] = match.slice(1).map(Number);
  const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
  const days = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  return year >= 1 && month >= 1 && month <= 12 && day >= 1 && day <= days[month - 1] && hour < 24 && minute < 60 && second < 60;
});
const load = (name: string) => {
  const schema = JSON.parse(readFileSync(ROOT + 'schemas/' + name, 'utf8'));
  const visit = (node: any) => {
    if (!node || typeof node !== 'object') return;
    for (const key of ['minimum', 'maximum', 'exclusiveMinimum', 'exclusiveMaximum']) {
      if (typeof node[key] === 'number' && (!Number.isFinite(node[key]) || Math.abs(node[key]) > Number.MAX_SAFE_INTEGER)) throw new Error('Schema outside S1 numeric profile');
    }
    if ('multipleOf' in node) throw new Error('Schema outside S1 numeric profile');
    if (node.uniqueItems) {
      const items = node.items;
      if (!(items?.type === 'string' || items?.enum?.every((x: any) => typeof x === 'string'))) throw new Error('Schema uniqueness outside S1 profile');
    }
    // Python re.search's terminal $ also permits a single final LF. Preserve
    // frozen schema meaning in the candidate compiler, not by editing schemas.
    if (typeof node.pattern === 'string' && node.pattern.endsWith('$') && !node.pattern.endsWith('\\$')) node.pattern = node.pattern.slice(0, -1) + '(?:\\n)?$';
    Object.values(node).forEach(visit);
  };
  visit(schema);
  return schema;
};
export const contractSchema = ajv.compile(load('qa-contract-v2.schema.json')) as ValidateFunction;
const assessmentV1 = load('qa-assessment-v1.schema.json');
export const assessment1 = ajv.compile(assessmentV1) as ValidateFunction;
export const assessment2 = ajv.compile(load('qa-assessment-v2.schema.json')) as ValidateFunction;
export const lifecycle = ajv.compile({ $ref: '#/$defs/lifecycleContext', $defs: assessmentV1.$defs }) as ValidateFunction;
export const reportSchema = ajv.compile(load('qa-offline-report-v1.schema.json')) as ValidateFunction;
export function schemaErrors(check: ValidateFunction, value: any, code: string): Issue[] {
  if (check(schemaValue(value))) return [];
  return (check.errors ?? []).map(error => ({ code, path: error.instancePath || '/', message: 'Schema constraint failed: ' + error.keyword }));
}
