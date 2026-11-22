#!/usr/bin/env node
/**
 * The types of the API, generated from the published contract.
 *
 * The contract is `docs/api/openapi.json` - the OpenAPI document the
 * application publishes. The client is typed against it, so the types are
 * generated from it rather than written by hand: a hand-written type is a
 * claim about the API, and a claim drifts.
 *
 * The generator reads the contract, follows the schemas the three commands
 * touch, and writes TypeScript interfaces for them. The drift test
 * regenerates this file and fails when the committed copy differs, so a
 * change in the contract that the client has not caught up with is a red
 * test rather than a surprise at runtime.
 *
 * Usage:
 *     node scripts/generate-types.mjs [--spec PATH] [--out PATH] [--check]
 */

import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const packageRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');

const DEFAULT_SPEC = resolve(packageRoot, '..', '..', 'docs', 'api', 'openapi.json');
const DEFAULT_OUT = resolve(packageRoot, 'src', 'generated', 'openapi.ts');

/**
 * The operations the client calls. Only these are typed: the client is a
 * command over three endpoints, not a second copy of the whole contract.
 */
const OPERATIONS = [
  { method: 'post', path: '/api/v1/tools/valuation' },
  { method: 'post', path: '/api/v1/search' },
  { method: 'post', path: '/api/v1/chat' },
];

function parseArgs(argv) {
  const options = { spec: DEFAULT_SPEC, out: DEFAULT_OUT, check: false };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === '--spec') {
      index += 1;
      options.spec = resolve(process.cwd(), argv[index] ?? '');
    } else if (arg === '--out') {
      index += 1;
      options.out = resolve(process.cwd(), argv[index] ?? '');
    } else if (arg === '--check') {
      options.check = true;
    } else {
      throw new Error(`Unknown argument: ${arg}`);
    }
  }
  return options;
}

/** The name of a schema, from a `$ref` into the components section. */
function refName(ref) {
  return String(ref).split('/').pop();
}

/**
 * The TypeScript type of a schema node.
 *
 * The mapping is deliberately narrow: a construct the generator does not
 * understand becomes `unknown` rather than a guess. `unknown` is the honest
 * answer - it compiles, and it says that the client does not know what the
 * server sends.
 */
function typeOf(node) {
  if (node === null || node === undefined) return 'unknown';
  if (typeof node !== 'object') return 'unknown';

  if (typeof node.$ref === 'string') return refName(node.$ref);

  if (Array.isArray(node.enum)) {
    return node.enum.map((value) => JSON.stringify(value)).join(' | ');
  }

  const union = node.anyOf ?? node.oneOf;
  if (Array.isArray(union)) {
    const parts = [];
    for (const member of union) {
      const rendered = typeOf(member);
      if (!parts.includes(rendered)) parts.push(rendered);
    }
    return parts.join(' | ') || 'unknown';
  }

  if (node.type === 'array') {
    const inner = typeOf(node.items ?? {});
    return inner.includes('|') ? `(${inner})[]` : `${inner}[]`;
  }

  if (node.properties) return inlineObject(node);

  if (node.additionalProperties && typeof node.additionalProperties === 'object') {
    return `Record<string, ${typeOf(node.additionalProperties)}>`;
  }

  switch (node.type) {
    case 'string':
      return 'string';
    case 'number':
    case 'integer':
      return 'number';
    case 'boolean':
      return 'boolean';
    case 'null':
      return 'null';
    case 'object':
      return 'Record<string, unknown>';
    default:
      return 'unknown';
  }
}

/** An object written out in place, because the contract does not name it. */
function inlineObject(node) {
  const required = new Set(node.required ?? []);
  const parts = [];
  for (const [key, value] of Object.entries(node.properties ?? {})) {
    const name = /^[A-Za-z_$][A-Za-z0-9_$]*$/.test(key) ? key : JSON.stringify(key);
    parts.push(`${name}${required.has(key) ? '' : '?'}: ${typeOf(value)}`);
  }
  return `{ ${parts.join('; ')} }`;
}

/** A description as a one-line JSDoc body. */
function docComment(text, indent = '') {
  if (!text) return '';
  const flat = String(text).replace(/\s+/g, ' ').replace(/\*\//g, '*\\/');
  return `${indent}/** ${flat} */\n`;
}

const IDENTIFIER = /^[A-Za-z_$][A-Za-z0-9_$]*$/;

/** One schema as a TypeScript declaration. */
function emitSchema(name, schema) {
  if (Array.isArray(schema.enum)) {
    return `${docComment(schema.description)}export type ${name} = ${typeOf(schema)};\n`;
  }

  const required = new Set(schema.required ?? []);
  const lines = [];
  for (const [key, value] of Object.entries(schema.properties ?? {})) {
    const propertyName = IDENTIFIER.test(key) ? key : JSON.stringify(key);
    const optional = required.has(key) ? '' : '?';
    lines.push(docComment(value.description, '  '));
    lines.push(`  ${propertyName}${optional}: ${typeOf(value)};\n`);
  }
  if (schema.additionalProperties === true) {
    lines.push('  [key: string]: unknown;\n');
  }

  const body = lines.join('');
  const declaration = body
    ? `export interface ${name} {\n${body}}\n`
    : `export interface ${name} {\n  [key: string]: unknown;\n}\n`;
  return `${docComment(schema.description)}${declaration}`;
}

/** Every schema the three operations reach. */
function reachableSchemas(spec) {
  const schemas = spec.components?.schemas ?? {};
  const found = new Set();

  const visit = (node) => {
    if (Array.isArray(node)) {
      node.forEach(visit);
      return;
    }
    if (!node || typeof node !== 'object') return;
    if (typeof node.$ref === 'string' && node.$ref.includes('/schemas/')) {
      const name = refName(node.$ref);
      if (!found.has(name)) {
        found.add(name);
        visit(schemas[name]);
      }
    }
    for (const value of Object.values(node)) visit(value);
  };

  for (const operation of OPERATIONS) {
    const methods = spec.paths?.[operation.path];
    if (!methods) {
      throw new Error(`The contract does not describe ${operation.path}`);
    }
    const definition = methods[operation.method];
    if (!definition) {
      throw new Error(`The contract does not describe ${operation.method} ${operation.path}`);
    }
    visit(definition.requestBody);
    visit(definition.responses);
  }

  return found;
}

function render(spec) {
  const schemas = spec.components?.schemas ?? {};
  const names = [...reachableSchemas(spec)].sort();

  let output = '';
  output += '/**\n';
  output += ' * The types of the public API, generated from the published contract.\n';
  output += ' *\n';
  output += " * Generated by `scripts/generate-types.mjs` from `docs/api/openapi.json`.\n";
  output += ' * Do not edit by hand: the drift test regenerates this file and fails\n';
  output += ' * when the committed copy differs from the contract.\n';
  output += ' */\n';
  output += '\n';
  output += '/* eslint-disable */\n';
  output += '\n';

  for (const name of names) {
    output += emitSchema(name, schemas[name] ?? {});
    output += '\n';
  }

  // The file ends with exactly one newline: the repository's end-of-file hook
  // fixes a second one, and a file the hook keeps changing is a file the
  // drift test keeps failing on.
  return `${output.replace(/\n+$/, '')}\n`;
}

function main() {
  const options = parseArgs(process.argv.slice(2));
  const spec = JSON.parse(readFileSync(options.spec, 'utf8'));
  const rendered = render(spec);

  if (options.check) {
    let current = '';
    try {
      current = readFileSync(options.out, 'utf8');
    } catch {
      current = '';
    }
    if (current !== rendered) {
      console.error('The generated types differ from the contract. Run: npm run generate:types');
      process.exit(1);
    }
    console.log('The generated types match the contract.');
    return;
  }

  mkdirSync(dirname(options.out), { recursive: true });
  writeFileSync(options.out, rendered, 'utf8');
  console.log(`Wrote ${options.out}`);
}

try {
  main();
} catch (error) {
  console.error(String(error instanceof Error ? error.message : error));
  process.exit(1);
}
