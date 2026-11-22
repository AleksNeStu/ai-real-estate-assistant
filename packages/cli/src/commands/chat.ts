/**
 * `propvector chat` - ask the assistant in one line.
 *
 * The answer is the assistant's own words, and the sources it rests on are
 * printed after it: an answer without its sources is an assertion.
 */

import type { ApiClient } from '../client.js';
import { OPERATIONS } from '../contract.js';
import type { ChatRequest, ChatResponse } from '../generated/openapi.js';
import { field, formatNumber } from '../format.js';

export interface ChatOptions {
  readonly message: string;
  readonly sessionId?: string;
}

/** The request the contract describes, with only the fields that were given. */
export function buildChatRequest(options: ChatOptions): ChatRequest {
  const request: ChatRequest = { message: options.message };
  if (options.sessionId) request.session_id = options.sessionId;
  return request;
}

export async function runChat(client: ApiClient, options: ChatOptions): Promise<ChatResponse> {
  return client.post<ChatResponse>(OPERATIONS.chat.relative, buildChatRequest(options));
}

/** The answer as a person reads it. */
export function formatChat(response: ChatResponse): string {
  const lines: string[] = [];
  lines.push(response.response ?? '');

  const sources = response.sources ?? [];
  if (sources.length) {
    lines.push('');
    lines.push(field('sources', formatNumber(sources.length)));
    for (const source of sources) {
      const title = typeof source['title'] === 'string' ? source['title'] : '';
      const url = typeof source['url'] === 'string' ? source['url'] : '';
      const label = title || url || JSON.stringify(source);
      lines.push(`  ${label}`);
    }
  }

  if (response.session_id) {
    lines.push('');
    lines.push(field('session', response.session_id));
  }

  return lines.join('\n');
}
