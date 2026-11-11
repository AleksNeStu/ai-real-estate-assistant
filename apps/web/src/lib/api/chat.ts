/**
 * Chat API: message sending, streaming chat with SSE parsing.
 */

import type { ChatRequest, ChatResponse } from '../types';

import { HeartbeatMonitor, StreamBuffer } from '../streaming';

import { getApiUrl, buildHeaders, safeFetch, handleResponse, ApiError } from './client';

// Re-export client types used in signatures
export type { ApiErrorCategory } from './client';

export async function chatMessage(request: ChatRequest): Promise<ChatResponse> {
  const response = await safeFetch(`${getApiUrl()}/chat`, {
    method: 'POST',
    headers: {
      ...buildHeaders(),
    },
    body: JSON.stringify(request),
  });
  return handleResponse<ChatResponse>(response);
}

export async function streamChatMessage(
  request: ChatRequest,
  onChunk: (chunk: string) => void,
  onStart?: (meta: { requestId?: string }) => void,
  onMeta?: (meta: {
    sources?: ChatResponse['sources'];
    sourcesTruncated?: boolean;
    sessionId?: string;
    intermediateSteps?: ChatResponse['intermediate_steps'];
    toolCalls?: ChatResponse['tool_calls'];
  }) => void,
  options?: {
    /** Enable heartbeat monitoring (default: true) */
    enableHeartbeat?: boolean;
    /** Heartbeat timeout in seconds (default: 45) */
    heartbeatTimeoutSeconds?: number;
    /** Enable stream buffering for recovery (default: false) */
    enableBuffer?: boolean;
    /** Session ID for buffer persistence */
    bufferSessionId?: string;
  }
): Promise<void> {
  const enableHeartbeat = options?.enableHeartbeat ?? true;
  const heartbeatTimeout = (options?.heartbeatTimeoutSeconds ?? 45) * 1000;
  const enableBuffer = options?.enableBuffer ?? false;

  // Initialize heartbeat monitor (Task #74)
  let heartbeatMonitor: HeartbeatMonitor | null = null;
  if (enableHeartbeat) {
    heartbeatMonitor = new HeartbeatMonitor({
      timeoutMs: heartbeatTimeout,
      onTimeout: () => {
        // Connection stalled - will throw error
        throw new Error(`Stream stalled: no data received for ${heartbeatTimeout / 1000} seconds`);
      },
    });
  }

  // Initialize stream buffer (Task #74)
  let streamBuffer: StreamBuffer | null = null;
  if (enableBuffer && options?.bufferSessionId) {
    streamBuffer = new StreamBuffer(options.bufferSessionId);
    // Attempt to restore from previous interrupted stream
    streamBuffer.restore();
  }

  const response = await safeFetch(`${getApiUrl()}/chat`, {
    method: 'POST',
    headers: {
      ...buildHeaders(),
    },
    body: JSON.stringify({ ...request, stream: true }),
  });

  if (!response.ok || !response.body) {
    const errorText = await response.text().catch(() => '');
    const headers = (response as unknown as { headers?: { get?: (name: string) => string | null } })
      .headers;
    const requestId =
      headers && typeof headers.get === 'function'
        ? headers.get('X-Request-ID') || undefined
        : undefined;
    const message = errorText || 'Failed to start stream';
    throw new ApiError(message, response.status, requestId || undefined);
  }

  const requestId = response.headers.get('X-Request-ID') || undefined;
  if (onStart) {
    onStart({ requestId });
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    // Record activity for heartbeat monitoring
    heartbeatMonitor?.recordActivity();

    buffer += decoder.decode(value);
    while (true) {
      const boundaryIndex = buffer.indexOf('\n\n');
      if (boundaryIndex === -1) break;
      const rawEvent = buffer.slice(0, boundaryIndex);
      buffer = buffer.slice(boundaryIndex + 2);

      let eventName = 'message';
      const dataLines: string[] = [];
      for (const rawLine of rawEvent.split('\n')) {
        const line = rawLine.trimEnd();
        if (!line) continue;
        // Handle SSE heartbeat comments (Task #74)
        if (line.startsWith(':')) {
          heartbeatMonitor?.handleHeartbeat();
          continue;
        }
        if (line.startsWith('event:')) {
          eventName = line.slice(6).trim() || 'message';
          continue;
        }
        if (line.startsWith('data:')) {
          dataLines.push(line.slice(5).trimStart());
        }
      }

      const data = dataLines.join('\n');
      if (!data) continue;
      if (data === '[DONE]') {
        // Clear buffer on successful completion
        streamBuffer?.clear();
        return;
      }

      let parsed: unknown = undefined;
      try {
        parsed = JSON.parse(data);
      } catch {
        parsed = undefined;
      }

      if (parsed && typeof parsed === 'object') {
        const maybeError = (parsed as { error?: unknown }).error;
        if (typeof maybeError === 'string' && maybeError.trim()) {
          // Persist buffer on error for potential recovery
          if (streamBuffer) {
            streamBuffer.persist();
          }
          throw new Error(maybeError);
        }

        if (eventName === 'meta') {
          if (onMeta) {
            const sources = (parsed as { sources?: unknown }).sources;
            const sourcesTruncated = (parsed as { sources_truncated?: unknown }).sources_truncated;
            const sessionId = (parsed as { session_id?: unknown }).session_id;
            const intermediateSteps = (parsed as { intermediate_steps?: unknown })
              .intermediate_steps;
            const toolCalls = (parsed as { tool_calls?: unknown }).tool_calls;
            onMeta({
              sources: Array.isArray(sources) ? (sources as ChatResponse['sources']) : undefined,
              sourcesTruncated:
                typeof sourcesTruncated === 'boolean' ? sourcesTruncated : undefined,
              sessionId: typeof sessionId === 'string' && sessionId.trim() ? sessionId : undefined,
              intermediateSteps: Array.isArray(intermediateSteps)
                ? (intermediateSteps as ChatResponse['intermediate_steps'])
                : undefined,
              toolCalls: Array.isArray(toolCalls)
                ? (toolCalls as ChatResponse['tool_calls'])
                : undefined,
            });
          }
          continue;
        }

        // Handle metrics event (Task #74)
        if (eventName === 'metrics') {
          // Metrics are informational, no action needed
          continue;
        }

        const content = (parsed as { content?: unknown }).content;
        if (typeof content === 'string') {
          // Buffer chunk for recovery (Task #74)
          if (streamBuffer) {
            streamBuffer.add(content);
          }
          onChunk(content);
          continue;
        }
      }

      // Buffer raw data as well
      if (streamBuffer) {
        streamBuffer.add(data);
      }
      onChunk(data);
    }
  }
}
