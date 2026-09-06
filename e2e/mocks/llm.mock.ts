/**
 * LLM response mocks for E2E tests.
 * Provides consistent mock responses for chat/AI assistant tests.
 */

import { Route, Request } from '@playwright/test';

/**
 * Mock LLM streaming response for chat tests.
 * Simulates SSE (Server-Sent Events) response.
 */
export function createMockLLMStreamResponse(
  chunks: string[] = [
    'Based on your search,',
    ' I found several properties',
    ' that match your criteria.',
    '\n\nHere are the options:',
    '\n1. A modern 2-bedroom apartment in Berlin Mitte for €1,200/month',
    '\n2. A spacious 3-bedroom flat in Prenzlauer Berg for €1,500/month',
    '\n\nWould you like more details?',
  ]
): string {
  const sseChunks = chunks.map((chunk) => `data: ${JSON.stringify({ content: chunk })}\n\n`);
  return sseChunks.join('') + 'data: [DONE]\n\n';
}

/**
 * Mock a successful chat API response.
 */
export async function mockChatSuccess(route: Route): Promise<void> {
  await route.fulfill({
    status: 200,
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Expose-Headers': 'X-Request-ID',
      'X-Request-ID': 'req-mock-chat-success',
    },
    body: createMockLLMStreamResponse(),
  });
}

/**
 * Mock a failed chat API response.
 */
export async function mockChatError(
  route: Route,
  statusCode: number = 500,
  message: string = 'Internal server error'
): Promise<void> {
  await route.fulfill({
    status: statusCode,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Expose-Headers': 'X-Request-ID',
      'X-Request-ID': `req-mock-chat-error-${statusCode}`,
    },
    body: JSON.stringify({ detail: message }),
  });
}

/**
 * Mock chat API with retry behavior.
 * Fails first N attempts, then succeeds.
 */
export function createMockChatWithRetry(failAttempts: number = 1) {
  let attempt = 0;

  return async (route: Route): Promise<void> => {
    const request = route.request();

    // Handle OPTIONS preflight
    if (request.method() === 'OPTIONS') {
      await route.fulfill({
        status: 204,
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'POST, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type, X-API-Key, X-User-Email',
          'Access-Control-Expose-Headers': 'X-Request-ID',
        },
        body: '',
      });
      return;
    }

    attempt++;

    if (attempt <= failAttempts) {
      await mockChatError(route, 500, `Simulated failure (attempt ${attempt})`);
      return;
    }

    await mockChatSuccess(route);
  };
}

/**
 * Mock chat response with property sources.
 */
export async function mockChatWithSources(route: Route): Promise<void> {
  const responseChunks = [
    'I found 2 properties matching your search:',
    '\n\n**Property 1**: Modern 2-Bedroom in Mitte - €1,200/month',
    '\n**Property 2**: Spacious 3-Bedroom in Prenzlauer Berg - €1,500/month',
    '\n\nBoth are available for immediate move-in.',
  ];

  const sseChunks = responseChunks.map(
    (chunk) => `data: ${JSON.stringify({ content: chunk })}\n\n`
  );

  // Add meta event with sources. The serializer in
  // apps/api/api/chat_sources.py emits each source as
  // {"content": str, "metadata": {...}} — mirror that shape so the
  // frontend (chat/page.tsx) renders the citations.
  const metaEvent = `event: meta\ndata: ${JSON.stringify({
    sources: [
      {
        content: 'Modern 2-Bedroom Apartment in Mitte',
        metadata: { id: 'prop-001', title: 'Modern 2-Bedroom Apartment in Mitte', score: 0.95 },
      },
      {
        content: 'Spacious 3-Bedroom Flat in Prenzlauer Berg',
        metadata: { id: 'prop-002', title: 'Spacious 3-Bedroom Flat in Prenzlauer Berg', score: 0.88 },
      },
    ],
    session_id: 'test-session-001',
  })}\n\n`;

  await route.fulfill({
    status: 200,
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Expose-Headers': 'X-Request-ID',
      'X-Request-ID': 'req-mock-chat-sources',
    },
    body: sseChunks.join('') + metaEvent + 'data: [DONE]\n\n',
  });
}
