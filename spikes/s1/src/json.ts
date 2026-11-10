// S1-only lossless JSON boundary. Never delegates candidate decisions to Python.
import { createHash } from 'node:crypto';

export type Doc = Record<string, any>;
export type Issue = { code: string; path?: string; message?: string };
export class InputError extends Error {
  constructor(public readonly issues: Issue[] = [{ code: 'E_INPUT' }]) { super('Invalid supplied input'); }
}

export class PyNumber {
  readonly integer: boolean;
  readonly value: bigint | number;
  constructor(readonly token: string) {
    this.integer = /^-?\d+$/.test(token);
    this.value = this.integer ? BigInt(token) : Number(token);
  }
  [Symbol.toPrimitive]() { return this.value; }
}

export function numericEqual(a: any, b: any): boolean {
  if (a instanceof PyNumber || b instanceof PyNumber) {
    const x = a instanceof PyNumber ? a.value : a;
    const y = b instanceof PyNumber ? b.value : b;
    if (typeof x === typeof y) return x === y;
    if (typeof x === 'bigint' && typeof y === 'number') return Number.isInteger(y) && x === BigInt(y);
    if (typeof y === 'bigint' && typeof x === 'number') return Number.isInteger(x) && y === BigInt(x);
    return false;
  }
  return a === b;
}

export function parse(text: string): any {
  let at = 0;
  const bad = (): never => { throw new InputError(); };
  const space = () => { while (/[\x20\t\r\n]/.test(text[at] ?? '') && at < text.length) at++; };
  const string = (): string => {
    const start = at++;
    while (at < text.length) {
      const c = text[at++];
      if (c === '"') {
        try { return JSON.parse(text.slice(start, at)); } catch { return bad(); }
      }
      if (c === '\\') at++;
    }
    return bad();
  };
  const value = (depth: number): any => {
    if (depth > 4096) return bad();
    space();
    const c = text[at];
    if (c === '"') return string();
    if (c === '{') {
      at++; space();
      const result = Object.create(null) as Doc;
      if (text[at] === '}') { at++; return result; }
      while (at < text.length) {
        space(); if (text[at] !== '"') return bad();
        const key = string();
        if (Object.hasOwn(result, key)) return bad();
        space(); if (text[at++] !== ':') return bad();
        result[key] = value(depth + 1); space();
        const separator = text[at++];
        if (separator === '}') return result;
        if (separator !== ',') return bad();
      }
      return bad();
    }
    if (c === '[') {
      at++; space();
      const result: any[] = [];
      if (text[at] === ']') { at++; return result; }
      while (at < text.length) {
        result.push(value(depth + 1)); space();
        const separator = text[at++];
        if (separator === ']') return result;
        if (separator !== ',') return bad();
      }
      return bad();
    }
    for (const [word, literal] of [['true', true], ['false', false], ['null', null]] as const) {
      if (text.startsWith(word, at)) { at += word.length; return literal; }
    }
    const number = /^-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?/.exec(text.slice(at));
    if (number) { at += number[0].length; return new PyNumber(number[0]); }
    return bad();
  };
  try {
    const result = value(0); space();
    if (at !== text.length) return bad();
    return result;
  } catch (error) {
    if (error instanceof InputError) throw error;
    throw new InputError();
  }
}

export function schemaValue(value: any): any {
  if (value instanceof PyNumber) {
    const number = Number(value.value);
    // Ajv sees only the schema profile guarded in schema.ts. Exact integer values
    // remain on the native document for equality, fencing, output and hashing.
    if (!Number.isFinite(number) && typeof value.value === 'bigint') return value.value < 0n ? -Number.MAX_VALUE : Number.MAX_VALUE;
    // Decimal overflow is valid JSON syntax in Python; Ajv's strict numeric type
    // check rejects Infinity where the frozen contract expects a finite integer.
    return number;
  }
  if (Array.isArray(value)) return value.map(schemaValue);
  if (value !== null && typeof value === 'object') {
    return Object.fromEntries(Object.entries(value).map(([k, v]) => [k, schemaValue(v)]));
  }
  return value;
}

function floatRepr(value: number): string {
  if (value === 0) return Object.is(value, -0) ? '-0.0' : '0.0';
  const sign = value < 0 ? '-' : '';
  const source = Math.abs(value).toString();
  let digits: string, exponent: number;
  if (source.includes('e')) {
    const [coefficient, power] = source.split('e');
    digits = coefficient.replace('.', ''); exponent = Number(power);
  } else {
    const [whole, fraction = ''] = source.split('.');
    if (whole !== '0') { digits = whole + fraction; exponent = whole.length - 1; }
    else { const first = fraction.search(/[1-9]/); digits = fraction.slice(first); exponent = -first - 1; }
  }
  digits = digits.replace(/0+$/, '');
  if (exponent < -4 || exponent >= 16) {
    return sign + digits[0] + (digits.length > 1 ? '.' + digits.slice(1) : '') + 'e' +
      (exponent < 0 ? '-' : '+') + Math.abs(exponent).toString().padStart(2, '0');
  }
  const point = exponent + 1;
  if (point <= 0) return sign + '0.' + '0'.repeat(-point) + digits;
  if (point >= digits.length) return sign + digits + '0'.repeat(point - digits.length) + '.0';
  return sign + digits.slice(0, point) + '.' + digits.slice(point);
}

function compareKeys(a: string, b: string): number {
  const x = Array.from(a), y = Array.from(b);
  for (let i = 0; i < Math.min(x.length, y.length); i++) {
    const delta = x[i].codePointAt(0)! - y[i].codePointAt(0)!;
    if (delta) return delta;
  }
  return x.length - y.length;
}

export function dump(value: any, ascii = false, digestMode = false): string {
  if (value instanceof PyNumber) {
    if (!value.integer && !Number.isFinite(value.value as number)) throw new InputError([{ code: 'E_INPUT_CANONICAL' }]);
    return value.integer ? value.value.toString() : floatRepr(value.value as number);
  }
  if (value === null || typeof value === 'boolean' || typeof value === 'number') return JSON.stringify(value);
  if (typeof value === 'string') {
    if (digestMode) {
      for (let i = 0; i < value.length; i++) {
        const c = value.charCodeAt(i);
        if (c >= 0xd800 && c <= 0xdbff) {
          const next = value.charCodeAt(++i);
          if (!(next >= 0xdc00 && next <= 0xdfff)) throw new InputError([{ code: 'E_INPUT_CANONICAL' }]);
        } else if (c >= 0xdc00 && c <= 0xdfff) throw new InputError([{ code: 'E_INPUT_CANONICAL' }]);
      }
    }
    let result = JSON.stringify(value);
    if (ascii) result = result.replace(/[\u007f-\uffff]/g, c => '\\u' + c.charCodeAt(0).toString(16).padStart(4, '0'));
    return result;
  }
  if (Array.isArray(value)) return '[' + value.map(v => dump(v, ascii, digestMode)).join(',') + ']';
  if (typeof value === 'object') return '{' + Object.keys(value).sort(compareKeys).map(k =>
    dump(k, ascii, digestMode) + ':' + dump(value[k], ascii, digestMode)).join(',') + '}';
  throw new InputError();
}

export function digest(value: any): string { return createHash('sha256').update(dump(value, false, true), 'utf8').digest('hex'); }
export function clone(value: any): any {
  if (value instanceof PyNumber) return new PyNumber(value.token);
  if (Array.isArray(value)) return value.map(clone);
  if (value !== null && typeof value === 'object') return Object.fromEntries(Object.entries(value).map(([k, v]) => [k, clone(v)]));
  return value;
}
export const subset = (a: Iterable<any>, b: Iterable<any>): boolean => { const dest = new Set(b); return Array.from(a).every(v => dest.has(v)); };
export const unique = (values: any[]): boolean => new Set(values.map(v => dump(v))).size === values.length;
