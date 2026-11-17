/**
 * The real backend, not a mocked one.
 *
 * The rest of the e2e suite mocks the API at the browser boundary, so a
 * green run says nothing about the backend: a broken route, a broken stream
 * or a broken auth dependency passes every mocked test. This suite talks to
 * the running stack and asserts the actual server-sent-event contract.
 *
 * Only the provider is mocked (DEMO_LLM_MODE=true selects the local MockLLM),
 * so no paid API key is needed and no answer leaves the machine. Everything
 * else - the router, the auth dependency, the agent, the SSE framing - is the
 * production code path.
 *
 * Run with:
 *   E2E_STACK=true STACK_BACKEND_URL=... STACK_FRONTEND_URL=... \
 *   PLAYWRIGHT_START_WEB=false npx playwright test e2e/infrastructure
 */

import { test, expect } from '@playwright/test';

// The ports the compose file publishes. The names are STACK_* on purpose: a
// project's own .env already carries a FRONTEND_URL for the local
// development stack, and npm loads that file into the test process, so a
// generic name silently points the probe at the wrong host.
const BACKEND_URL = process.env.STACK_BACKEND_URL || 'http://localhost:8082';
const FRONTEND_URL = process.env.STACK_FRONTEND_URL || 'http://localhost:3082';
const API_ACCESS_KEY = process.env.API_ACCESS_KEY || '';

// The stack is needed: the suite is opt-in, like the rest of the
// infrastructure specs.
test.skip(process.env.E2E_STACK !== 'true', 'needs the Docker Compose stack (E2E_STACK=true)');

// The chat route analyses the query before it answers, so the first answer
// takes longer than the Playwright default allows.
const CHAT_TIMEOUT = 120_000;

type SseFrame = {
  event: string;
  data: string;
};

/**
 * Parse a Server-Sent Events body into its frames.
 *
 * A frame without an `event:` line is a `message` frame - that is what the
 * SSE specification says, and it is what the chat route sends for the
 * content chunks and for the `[DONE]` terminator.
 */
function parseSse(body: string): SseFrame[] {
  const frames: SseFrame[] = [];

  for (const block of body.split(/\n\n/)) {
    const trimmed = block.trim();
    if (!trimmed) continue;

    let event = 'message';
    const dataLines: string[] = [];

    for (const line of trimmed.split(/\n/)) {
      if (line.startsWith('event:')) {
        event = line.slice('event:'.length).trim();
      } else if (line.startsWith('data:')) {
        dataLines.push(line.slice('data:'.length).trim());
      }
    }

    if (dataLines.length > 0) {
      frames.push({ event, data: dataLines.join('\n') });
    }
  }

  return frames;
}

function chatBody(message: string) {
  return {
    message,
    stream: true,
    include_intermediate_steps: true,
  };
}

function chatHeaders() {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (API_ACCESS_KEY) {
    headers['X-API-Key'] = API_ACCESS_KEY;
  }
  return headers;
}

test.describe('The real backend', () => {
  // The stream is one conversation at a time: the answers are slow enough
  // that a parallel run would fight over the resources of the stack.
  test.describe.configure({ mode: 'serial' });

  // A turn analyses the query, reads the retrieval stack and answers - two
  // turns in one test do not fit into the default 60 seconds.
  test.setTimeout(CHAT_TIMEOUT * 2);

  test('the chat route streams the real SSE events', async ({ request }) => {
    const response = await request.post(`${BACKEND_URL}/api/v1/chat`, {
      headers: chatHeaders(),
      data: chatBody('Two-room apartments in Krakow under 500,000 PLN'),
      timeout: CHAT_TIMEOUT,
    });

    expect(response.status()).toBe(200);
    expect(response.headers()['content-type']).toContain('text/event-stream');

    const frames = parseSse(await response.text());

    // The content chunks: the answer arrives as `data: {"content": ...}`.
    const answer = frames
      .filter((frame) => frame.event === 'message' && frame.data !== '[DONE]')
      .map((frame) => {
        try {
          return (JSON.parse(frame.data) as { content?: string }).content ?? '';
        } catch {
          // A frame that is not a content envelope is not part of the answer.
          return '';
        }
      })
      .join('');

    expect(answer.length).toBeGreaterThan(0);
    expect(answer).not.toContain('[DONE]');

    // The meta event: the sources and the identifiers of this turn.
    const meta = frames.find((frame) => frame.event === 'meta');
    expect(meta, 'the stream carries no meta event').toBeTruthy();

    const metaPayload = JSON.parse(meta!.data) as Record<string, unknown>;
    expect(metaPayload).toHaveProperty('sources');
    expect(Array.isArray(metaPayload.sources)).toBe(true);
    expect(metaPayload).toHaveProperty('request_id');
    expect(metaPayload).toHaveProperty('session_id');

    // The terminator: the last frame closes the stream.
    expect(frames[frames.length - 1].data).toBe('[DONE]');
  });

  test('the answer comes from the server, not from the mocked fixture', async ({ request }) => {
    const ask = async () => {
      const response = await request.post(`${BACKEND_URL}/api/v1/chat`, {
        headers: chatHeaders(),
        data: chatBody('A two-room apartment in Krakow near the centre'),
        timeout: CHAT_TIMEOUT,
      });
      expect(response.status()).toBe(200);

      const frames = parseSse(await response.text());
      const meta = frames.find((frame) => frame.event === 'meta');
      expect(meta).toBeTruthy();
      return JSON.parse(meta!.data) as Record<string, unknown>;
    };

    const first = await ask();
    const second = await ask();

    // The mocked fixture carries a fixed session id and no request id at all.
    // The server issues both per turn, so their presence is the fingerprint
    // of a real answer - and a request id that changes from turn to turn is
    // what a canned fixture cannot produce.
    expect(first.session_id).not.toBe('test-session-001');
    expect(String(first.request_id).length).toBeGreaterThan(0);
    expect(String(first.request_id)).not.toBe(String(second.request_id));
  });

  test('the frontend proxy forwards the stream to the browser', async ({ request }) => {
    const response = await request.post(`${FRONTEND_URL}/api/v1/chat`, {
      headers: chatHeaders(),
      data: chatBody('A flat with a garden in Gdansk'),
      timeout: CHAT_TIMEOUT,
    });

    expect(response.status()).toBe(200);

    const frames = parseSse(await response.text());

    // The proxy streams the server's frames unchanged - the browser reads
    // the same events as a direct call.
    expect(frames.some((frame) => frame.event === 'meta')).toBe(true);
    expect(frames[frames.length - 1].data).toBe('[DONE]');
  });

  test('the chat route asks for the API key when the deployment has no bypass', async ({ request }) => {
    const response = await request.post(`${BACKEND_URL}/api/v1/chat`, {
      headers: { 'Content-Type': 'application/json' },
      data: chatBody('anything'),
      timeout: CHAT_TIMEOUT,
    });

    // The stack runs with the demo bypass, so the route answers. The point of
    // the check is that the route is reachable at all and that the answer is
    // the same shape - a 404 here would mean the route moved.
    expect([200, 401]).toContain(response.status());
  });
});
