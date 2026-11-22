/**
 * The request layer, against a recorded answer.
 *
 * The client is asked to make exactly the request the contract describes, and
 * to read exactly the answer the server recorded.
 */

import assert from 'node:assert/strict';
import { describe, it } from 'node:test';

import { ApiClient, ApiError, NetworkError } from '../client.js';
import { OPERATIONS } from '../contract.js';
import { buildValuationRequest } from '../commands/valuation.js';
import { buildSearchRequest } from '../commands/search.js';
import { buildChatRequest } from '../commands/chat.js';
import type { ValuationResponse, SearchResponse, ChatResponse } from '../generated/openapi.js';
import { fixtureText } from './helpers.js';

const KEY = 'pv-test-key-not-a-real-secret';

describe('the request layer', () => {
  it('posts the valuation to the path the contract names, with the key in the header', async () => {
    const calls: { url: string; init?: RequestInit }[] = [];
    const client = new ApiClient(
      { baseUrl: 'http://api.invalid/api/v1', apiKey: KEY },
      async (url, init) => {
        calls.push({ url, init });
        return new Response(fixtureText('valuation.response.json'), { status: 200 });
      },
    );

    const request = buildValuationRequest({
      city: 'Kraków',
      street: 'Myśliwska',
      areaSqm: 60,
      rooms: 3,
    });
    const answer = await client.post<ValuationResponse>(OPERATIONS.valuation.relative, request);

    assert.equal(calls.length, 1);
    assert.equal(calls[0]?.url, 'http://api.invalid/api/v1/tools/valuation');
    assert.equal(calls[0]?.init?.method, 'POST');
    const headers = calls[0]?.init?.headers as Record<string, string>;
    assert.equal(headers['X-API-Key'], KEY);
    assert.equal(headers['Content-Type'], 'application/json');
    assert.deepEqual(JSON.parse(String(calls[0]?.init?.body)), {
      city: 'Kraków',
      street: 'Myśliwska',
      area_sqm: 60,
      rooms: 3,
    });

    assert.equal(answer.estimated_value, 959182);
    assert.equal(answer.currency, 'PLN');
    assert.equal(answer.comparables?.length, 2);
  });

  it('sends only the fields it was given', () => {
    assert.deepEqual(buildValuationRequest({ city: 'Kraków', street: 'Myśliwska' }), {
      city: 'Kraków',
      street: 'Myśliwska',
    });
    assert.deepEqual(buildSearchRequest({ query: 'flats in Krakow', limit: 5 }), {
      query: 'flats in Krakow',
      limit: 5,
    });
    assert.deepEqual(buildChatRequest({ message: 'how much' }), { message: 'how much' });
  });

  it('reads a recorded search answer', async () => {
    const client = new ApiClient(
      { baseUrl: 'http://api.invalid/api/v1', apiKey: KEY },
      async () => new Response(fixtureText('search.response.json'), { status: 200 }),
    );
    const answer = await client.post<SearchResponse>(
      OPERATIONS.search.relative,
      buildSearchRequest({ query: 'flats in Krakow' }),
    );
    assert.equal(answer.count, 2);
    assert.equal(answer.results?.[0]?.property.city, 'Kraków');
    assert.equal(answer.results?.[0]?.score, 0.91);
  });

  it('reads a recorded chat answer', async () => {
    const client = new ApiClient(
      { baseUrl: 'http://api.invalid/api/v1', apiKey: KEY },
      async () => new Response(fixtureText('chat.response.json'), { status: 200 }),
    );
    const answer = await client.post<ChatResponse>(
      OPERATIONS.chat.relative,
      buildChatRequest({ message: 'what does a flat in Krakow cost' }),
    );
    assert.match(answer.response, /notarial sales/);
    assert.equal(answer.sources?.length, 1);
  });

  it('never puts the key in the URL', async () => {
    let seen = '';
    const client = new ApiClient(
      { baseUrl: 'http://api.invalid/api/v1', apiKey: KEY },
      async (url) => {
        seen = url;
        return new Response('{}', { status: 200 });
      },
    );
    await client.post('/tools/valuation', {});
    assert.equal(seen.includes(KEY), false);
  });

  it('reports what the server answered when the answer is not a success', async () => {
    const client = new ApiClient(
      { baseUrl: 'http://api.invalid/api/v1', apiKey: KEY },
      async () => new Response('{"detail":"Not Found"}', { status: 404 }),
    );
    await assert.rejects(
      () => client.post('/tools/valuation', {}),
      (error: unknown) => {
        assert.ok(error instanceof ApiError);
        assert.equal(error.status, 404);
        assert.match(error.message, /404/);
        assert.equal(error.message.includes(KEY), false);
        return true;
      },
    );
  });

  it('says so when the server cannot be reached', async () => {
    const client = new ApiClient(
      { baseUrl: 'http://api.invalid/api/v1', apiKey: KEY },
      async () => {
        throw new Error('ECONNREFUSED');
      },
    );
    await assert.rejects(
      () => client.post('/tools/valuation', {}),
      (error: unknown) => {
        assert.ok(error instanceof NetworkError);
        assert.match(error.message, /did not answer/);
        assert.equal(error.message.includes(KEY), false);
        return true;
      },
    );
  });
});
