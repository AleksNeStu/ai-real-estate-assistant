/**
 * The client against the published contract.
 *
 * The contract is `docs/api/openapi.json`. The client may not call an
 * endpoint the contract does not describe, may not send a field the contract
 * does not describe, and may not read a field the contract does not describe.
 * When the contract moves and the client has not followed, this test is red.
 */

import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, it } from 'node:test';

import { OPERATIONS } from '../contract.js';
import { buildValuationRequest } from '../commands/valuation.js';
import { buildSearchRequest } from '../commands/search.js';
import { buildChatRequest } from '../commands/chat.js';
import { packageRoot } from './helpers.js';

const ROOT = packageRoot();
const SPEC_PATH = resolve(ROOT, '..', '..', 'docs', 'api', 'openapi.json');

interface Schema {
  properties?: Record<string, unknown>;
  required?: string[];
  type?: string;
}

interface OperationDefinition {
  requestBody?: { content: Record<string, { schema: unknown }> };
  responses: Record<string, { content?: Record<string, { schema: unknown }> } | undefined>;
}

const spec = JSON.parse(readFileSync(SPEC_PATH, 'utf8')) as {
  paths: Record<string, Record<string, OperationDefinition | undefined>>;
  components: { schemas: Record<string, Schema> };
};

/** The schema a `$ref` points at. */
function resolveSchema(node: unknown): Schema {
  if (!node || typeof node !== 'object') return {};
  const ref = (node as { $ref?: string }).$ref;
  if (typeof ref === 'string' && ref.includes('/schemas/')) {
    return spec.components.schemas[ref.split('/').pop() ?? ''] ?? {};
  }
  return node as Schema;
}

/** The request schema of an operation. */
function requestSchema(operation: { path: string; method: string }): Schema {
  const definition = spec.paths[operation.path]?.[operation.method];
  assert.ok(definition, `the contract does not describe ${operation.method} ${operation.path}`);
  return resolveSchema(definition.requestBody?.content?.['application/json']?.schema);
}

/** The 200 response schema of an operation. */
function responseSchema(operation: { path: string; method: string }): Schema {
  const definition = spec.paths[operation.path]?.[operation.method];
  assert.ok(definition, `the contract does not describe ${operation.method} ${operation.path}`);
  return resolveSchema(definition.responses['200']?.content?.['application/json']?.schema);
}

/** The fields each command sends when everything is given. */
const SENT: Record<string, string[]> = {
  valuation: Object.keys(
    buildValuationRequest({
      city: 'Kraków',
      street: 'Myśliwska',
      areaSqm: 60,
      rooms: 3,
      propertyId: 'prop-001',
    }),
  ),
  search: Object.keys(
    buildSearchRequest({
      query: 'flats',
      limit: 5,
      sortBy: 'price',
      sortOrder: 'asc',
    }),
  ),
  chat: Object.keys(buildChatRequest({ message: 'hello', sessionId: 'session-001' })),
};

/** The fields each command reads out of the answer. */
const READ: Record<string, string[]> = {
  valuation: [
    'estimated_value',
    'currency',
    'low',
    'high',
    'price_per_sqm_median',
    'comparison_area',
    'period_start',
    'period_end',
    'sample_size',
    'source',
    'confidence',
    'notes',
    'comparables',
  ],
  search: ['count', 'results'],
  chat: ['response', 'sources', 'session_id'],
};

describe('the published contract', () => {
  for (const [name, operation] of Object.entries(OPERATIONS)) {
    it(`describes ${operation.method.toUpperCase()} ${operation.path}`, () => {
      const definition = spec.paths[operation.path]?.[operation.method];
      assert.ok(
        definition,
        `the contract does not describe ${operation.method} ${operation.path}`,
      );
    });

    it(`describes every field the ${name} command sends`, () => {
      const properties = requestSchema(operation).properties ?? {};
      for (const field of SENT[name] ?? []) {
        assert.ok(
          field in properties,
          `the contract does not describe the request field "${field}" of ${name}`,
        );
      }
    });

    it(`asks for everything the ${name} command requires`, () => {
      const schema = requestSchema(operation);
      const properties = schema.properties ?? {};
      for (const field of schema.required ?? []) {
        assert.ok(
          field in properties,
          `the contract requires "${field}" of ${name}, which the client cannot send`,
        );
        assert.ok(
          (SENT[name] ?? []).includes(field),
          `the client never sends the required field "${field}" of ${name}`,
        );
      }
    });

    it(`describes every field the ${name} command reads`, () => {
      const properties = responseSchema(operation).properties ?? {};
      for (const field of READ[name] ?? []) {
        assert.ok(
          field in properties,
          `the contract does not describe the answer field "${field}" of ${name}`,
        );
      }
    });
  }

  it('has generated types that match the contract', () => {
    const result = spawnSync(
      process.execPath,
      [resolve(ROOT, 'scripts', 'generate-types.mjs'), '--check'],
      { cwd: ROOT, encoding: 'utf8' },
    );
    assert.equal(
      result.status,
      0,
      `the generated types differ from the contract:\n${result.stdout}\n${result.stderr}`,
    );
  });
});
