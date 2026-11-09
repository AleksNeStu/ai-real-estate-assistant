'use client';

import { useState, useRef, useEffect, useMemo } from 'react';
import { Send, Loader2, Lightbulb, RefreshCw, Info } from 'lucide-react';
import { cn } from '@/lib/utils';
import { streamChatMessage, ApiError } from '@/lib/api';
import type { ChatResponse, EnhancedCitation, CitationStats } from '@/lib/types';
import CitationDisplay from '@/components/CitationDisplay';
import { useTranslations } from 'next-intl';

import { MonoAnnotation } from '@/components/ui/mono-annotation';
import { ToolCard } from '@/components/ui/tool-card';
import { ContextPane } from '@/components/chat/context-pane';
import { ToolResult } from '@/components/chat/tool-result';
import { parseToolCalls, type ToolCall } from '@/components/chat/tool-calls';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  sources?: ChatResponse['sources'];
  sourcesTruncated?: boolean;
  citationStats?: CitationStats | null;
  intermediateSteps?: ChatResponse['intermediate_steps'];
  /** The calls the agent made to answer this turn. */
  toolCalls?: ToolCall[];
  isError?: boolean;
  requestId?: string;
}

export default function ChatPage() {
  const t = useTranslations('chat');
  const tError = useTranslations('error');

  // Suggested prompts for empty state
  const suggestedPrompts = [
    t('examplePrompts.madrid'),
    t('examplePrompts.krakow'),
    t('examplePrompts.warsaw'),
    t('examplePrompts.mortgage'),
    t('examplePrompts.gardens'),
  ];

  // Track if user has sent any message (for empty state)
  const [hasStarted, setHasStarted] = useState(false);

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | undefined>(undefined);
  const [lastUserMessage, setLastUserMessage] = useState<string | undefined>(undefined);
  const [debugMode, setDebugMode] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const formRef = useRef<HTMLFormElement>(null);

  // Every call the assistant made, in the order it made them. The context
  // pane indexes them; the cards in the conversation are the same calls.
  const toolCalls = useMemo(
    () =>
      messages.flatMap((message, messageIndex) =>
        (message.toolCalls ?? []).map((call, callIndex) => ({
          id: `tool-${messageIndex}-${callIndex}`,
          name: call.name,
        }))
      ),
    [messages]
  );

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const applyStreamError = (error: unknown, isRetry: boolean = false) => {
    let message = tError('generic');
    let requestId: string | undefined = undefined;

    if (error instanceof ApiError) {
      message = error.message;
      requestId = error.request_id;
    } else if (error instanceof Error) {
      message = error.message;
      // Try to extract request_id from error message
      const match = message.match(/request_id=([A-Za-z0-9_-]+)/i);
      if (match && match[1]) {
        requestId = match[1];
      }
    }

    setMessages((prev) => {
      const updated = [...prev];
      const lastIdx = updated.length - 1;

      if (isRetry) {
        // Replace the temporary loading message with error
        if (lastIdx >= 0 && updated[lastIdx].role === 'assistant' && !updated[lastIdx].content) {
          updated[lastIdx] = {
            ...updated[lastIdx],
            content: t('errors.apology', { error: message }),
            isError: true,
            requestId,
          };
          return updated;
        }
      }

      return [
        ...updated,
        {
          role: 'assistant',
          content: t('errors.apology', { error: message }),
          isError: true,
          requestId,
        },
      ];
    });
  };

  const handleSuggestedPrompt = (prompt: string) => {
    setInput(prompt);
    setTimeout(() => {
      formRef.current?.requestSubmit();
    }, 100);
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const params = new URLSearchParams(window.location.search);
    setDebugMode(params.get('debug') === '1');
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput('');
    setHasStarted(true);
    setMessages((prev) => [...prev, { role: 'user', content: userMessage }]);
    setIsLoading(true);
    setLastUserMessage(userMessage);

    try {
      const sid =
        sessionId ??
        (typeof crypto !== 'undefined' && 'randomUUID' in crypto ? crypto.randomUUID() : undefined);
      if (sid && !sessionId) {
        setSessionId(sid);
      }

      // Add empty assistant message that will be filled with streamed content
      setMessages((prev) => [...prev, { role: 'assistant', content: '' }]);

      await streamChatMessage(
        { message: userMessage, session_id: sid, include_intermediate_steps: true },
        (chunk) => {
          setMessages((prev) => {
            const updated = [...prev];
            const lastIdx = updated.length - 1;
            if (lastIdx >= 0 && updated[lastIdx].role === 'assistant') {
              updated[lastIdx] = { ...updated[lastIdx], content: updated[lastIdx].content + chunk };
            }
            return updated;
          });
        },
        () => {
          // requestId is available but not currently displayed
        },
        ({ sources, sourcesTruncated, sessionId: returnedSessionId, intermediateSteps }) => {
          if (returnedSessionId && !sessionId) setSessionId(returnedSessionId);
          setMessages((prev) => {
            const updated = [...prev];
            const lastIdx = updated.length - 1;
            if (lastIdx >= 0 && updated[lastIdx].role === 'assistant') {
              const toolCalls = parseToolCalls(intermediateSteps);
              updated[lastIdx] = {
                ...updated[lastIdx],
                sources: sources && sources.length ? sources : updated[lastIdx].sources,
                sourcesTruncated:
                  typeof sourcesTruncated === 'boolean'
                    ? sourcesTruncated
                    : updated[lastIdx].sourcesTruncated,
                intermediateSteps:
                  intermediateSteps && intermediateSteps.length
                    ? intermediateSteps
                    : updated[lastIdx].intermediateSteps,
                toolCalls: toolCalls.length ? toolCalls : updated[lastIdx].toolCalls,
              };
            }
            return updated;
          });
        }
      );
    } catch (error) {
      applyStreamError(error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRetry = async () => {
    if (!lastUserMessage || isLoading) return;
    setIsLoading(true);
    setMessages((prev) => [...prev, { role: 'assistant', content: '' }]);

    try {
      await streamChatMessage(
        { message: lastUserMessage, session_id: sessionId, include_intermediate_steps: true },
        (chunk) => {
          setMessages((prev) => {
            const updated = [...prev];
            const lastIdx = updated.length - 1;
            if (lastIdx >= 0 && updated[lastIdx].role === 'assistant') {
              updated[lastIdx] = { ...updated[lastIdx], content: updated[lastIdx].content + chunk };
            }
            return updated;
          });
        },
        () => {
          // requestId is available but not currently displayed
        },
        ({ sources, sourcesTruncated, intermediateSteps }) => {
          setMessages((prev) => {
            const updated = [...prev];
            const lastIdx = updated.length - 1;
            if (lastIdx >= 0 && updated[lastIdx].role === 'assistant') {
              const toolCalls = parseToolCalls(intermediateSteps);
              updated[lastIdx] = {
                ...updated[lastIdx],
                sources: sources && sources.length ? sources : updated[lastIdx].sources,
                sourcesTruncated:
                  typeof sourcesTruncated === 'boolean'
                    ? sourcesTruncated
                    : updated[lastIdx].sourcesTruncated,
                intermediateSteps:
                  intermediateSteps && intermediateSteps.length
                    ? intermediateSteps
                    : updated[lastIdx].intermediateSteps,
                toolCalls: toolCalls.length ? toolCalls : updated[lastIdx].toolCalls,
              };
            }
            return updated;
          });
        }
      );
    } catch (error) {
      applyStreamError(error, true);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex h-[calc(100vh-4rem)]">
      {/* The chat shows its title in the welcome panel only, so the route
          would lose its H1 as soon as the first message arrives. One heading
          stays in the document either way: hidden once the conversation
          starts. */}
      <h1 className="sr-only">{t('title')}</h1>
      <main className="flex min-w-0 flex-1 flex-col">
        <div className="flex flex-1 overflow-y-auto">
          <div className="mx-auto flex w-full max-w-[780px] flex-col gap-7 px-6 py-7">
            {/* The demo banner: the honest note about the model behind the answer. */}
            <div
              className="flex items-center justify-center gap-2.5 rounded-md bg-muted px-3 py-2 text-annot text-muted-foreground"
              role="status"
            >
              <span className="size-1.5 shrink-0 rounded-full bg-success" aria-hidden="true" />
              <span>{t('poweredBy.description')}</span>
            </div>

            {/* STATE 1: Empty state (zero-data) - before user starts */}
            {!hasStarted && messages.length === 0 && (
              <div
                className="flex flex-col items-start gap-4 py-10"
                role="status"
                aria-live="polite"
              >
                <div className="flex flex-col gap-2">
                  <p className="m-0 text-section font-semibold text-foreground">{t('title')}</p>
                  <p className="m-0 max-w-md text-body text-muted-foreground">{t('description')}</p>
                </div>
                <div className="flex flex-col gap-2">
                  <span className="flex items-center gap-2 text-annot text-muted-foreground">
                    <Lightbulb className="size-4" aria-hidden="true" />
                    {t('emptyState.suggestions')}
                  </span>
                  <div className="flex flex-wrap gap-2">
                    {suggestedPrompts.map((prompt, idx) => (
                      <button
                        key={idx}
                        type="button"
                        data-testid="chat-suggestion"
                        onClick={() => handleSuggestedPrompt(prompt)}
                        className="rounded-full border border-border px-3 py-1.5 text-app text-foreground transition-colors hover:bg-muted disabled:opacity-50"
                        disabled={isLoading}
                      >
                        {prompt}
                      </button>
                    ))}
                  </div>
                </div>
                <p className="m-0 max-w-md text-annot text-muted-foreground">
                  {t('poweredBy.description')}
                </p>
              </div>
            )}

            {/* STATE 2: Loading state (streaming) - thinking indicator */}
            {isLoading && (
              <div
                className="flex items-center gap-3"
                role="status"
                aria-live="polite"
                aria-label={t('loading.thinking')}
              >
                <AssistantMark />
                <div className="flex items-center gap-2">
                  <Loader2 className="size-4 animate-spin text-muted-foreground" />
                  <span className="text-app text-muted-foreground">{t('loading.thinking')}</span>
                </div>
              </div>
            )}

            {/* STATE 3 & 4: Message list (Populated state + inline errors) */}
            {messages.map((message, index) =>
              message.role === 'user' ? (
                <div key={index} className="flex justify-end">
                  <p
                    data-testid="chat-user-message"
                    className="m-0 max-w-[580px] rounded-lg bg-muted px-3.5 py-2.5 text-app text-foreground"
                  >
                    {message.content}
                  </p>
                </div>
              ) : (
                <div
                  key={index}
                  data-testid="chat-assistant-message"
                  className="grid grid-cols-[28px_minmax(0,1fr)] gap-3.5"
                  role={message.isError ? 'alert' : undefined}
                  aria-live={message.isError ? 'assertive' : 'polite'}
                >
                  <AssistantMark />
                  <div className="flex min-w-0 flex-col gap-3">
                    <div className="break-words text-app leading-relaxed text-foreground">
                      {!message.content ? (
                        <span className="text-muted-foreground">{t('loading.thinking')}</span>
                      ) : (
                        message.content
                      )}
                    </div>

                    {/* The calls the agent made, one card each. */}
                    {message.toolCalls && message.toolCalls.length > 0 ? (
                      <div className="flex flex-col gap-3">
                        {message.toolCalls.map((call, callIndex) => (
                          <div
                            key={`tool-${index}-${callIndex}`}
                            id={`tool-${index}-${callIndex}`}
                            className="scroll-mt-4"
                          >
                            <ToolCard
                              name={call.name}
                              args={call.args}
                              result={<ToolResult observation={call.result} />}
                              resultLabel={t('toolCard.result')}
                              stepsLabel={t('toolCard.steps')}
                              sourcesLabel={t('toolCard.sources')}
                            />
                          </div>
                        ))}
                      </div>
                    ) : null}

                    {/* The sources belong to the answer, not to a card. */}
                    {message.sources && message.sources.length > 0 && (
                      <CitationDisplay
                        citations={message.sources.map((source): EnhancedCitation => {
                          const metadata = source.metadata || {};
                          // Check if already enhanced citation format
                          if ('source_type' in metadata && 'confidence' in metadata) {
                            return {
                              source: metadata.source as string | undefined,
                              chunk_index: metadata.chunk_index as number | undefined,
                              page_number: metadata.page_number as number | undefined,
                              paragraph_number: metadata.paragraph_number as number | undefined,
                              source_type:
                                (metadata.source_type as EnhancedCitation['source_type']) || 'unknown',
                              confidence:
                                (metadata.confidence as EnhancedCitation['confidence']) || 'medium',
                              confidence_score: (metadata.confidence_score as number) || 0.5,
                              content_snippet: source.content || null,
                              source_url: metadata.source_url as string | undefined,
                              source_title: metadata.source_title as string | undefined,
                              citation_hash: metadata.citation_hash as string | undefined,
                              is_duplicate: (metadata.is_duplicate as boolean) || false,
                              validated: (metadata.validated as boolean) || false,
                            };
                          }
                          // Legacy format - convert to enhanced
                          return {
                            source: metadata.source as string | undefined,
                            chunk_index: metadata.chunk_index as number | undefined,
                            page_number: metadata.page_number as number | undefined,
                            paragraph_number: metadata.paragraph_number as number | undefined,
                            source_type: 'unknown',
                            confidence: 'medium',
                            confidence_score: 0.5,
                            content_snippet: source.content || null,
                            source_url: undefined,
                            source_title:
                              (metadata.title as string | undefined) ||
                              (metadata.source as string | undefined),
                            citation_hash: undefined,
                            is_duplicate: false,
                            validated: false,
                          };
                        })}
                        stats={message.citationStats}
                        truncated={message.sourcesTruncated}
                      />
                    )}

                    {/* Intermediate steps (debug mode) */}
                    {debugMode &&
                      message.intermediateSteps &&
                      message.intermediateSteps.length > 0 && (
                        <details className="rounded-md border bg-muted/30 px-3 py-2 text-xs">
                          <summary className="cursor-pointer select-none font-medium">
                            {t('debug.trace', { count: message.intermediateSteps.length })}
                          </summary>
                          <pre className="mt-2 whitespace-pre-wrap break-words font-mono text-[11px] leading-snug">
                            {JSON.stringify(message.intermediateSteps, null, 2)}
                          </pre>
                        </details>
                      )}

                    {/* Error retry button */}
                    {message.isError && (
                      <div className="flex items-center gap-3">
                        {message.requestId && (
                          <MonoAnnotation>{t('retry.requestId', { id: message.requestId })}</MonoAnnotation>
                        )}
                        <button
                          type="button"
                          onClick={handleRetry}
                          disabled={isLoading}
                          className="inline-flex items-center gap-2 rounded-md bg-action px-3 py-1.5 text-xs font-medium text-action-foreground transition-colors hover:bg-action/90 focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50 disabled:opacity-50"
                        >
                          <RefreshCw className="size-3" />
                          {t('retry.button')}
                        </button>
                      </div>
                    )}

                    {/* The disclosure the law asks for, at the end of the answer. */}
                    {message.content && !message.isError ? (
                      <div className="flex items-start gap-2 text-annot text-muted-foreground">
                        <Info className="mt-0.5 size-3 shrink-0" aria-hidden="true" />
                        <p className="m-0">{t('aiDisclaimer')}</p>
                      </div>
                    ) : null}
                  </div>
                </div>
              )
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* The composer */}
        <form
          ref={formRef}
          onSubmit={handleSubmit}
          className="mx-auto flex w-full max-w-[780px] flex-col gap-2.5 px-6 pb-6 pt-4"
        >
          <div className="flex gap-2">
            <input
              data-testid="chat-input"
              className="h-12 flex-1 rounded-lg border border-input bg-background px-3.5 text-app file:border-0 file:bg-transparent file:text-app file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50 disabled:cursor-not-allowed disabled:opacity-50"
              placeholder={hasStarted ? t('input.placeholderStarted') : t('input.placeholderEmpty')}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={isLoading}
              aria-label={t('input.ariaLabel')}
            />
            <button
              type="submit"
              data-testid="chat-send"
              aria-label={isLoading ? t('input.ariaLabelSending') : t('input.ariaLabelSend')}
              disabled={isLoading || !input.trim()}
              className="inline-flex size-12 items-center justify-center rounded-lg bg-action text-action-foreground transition-colors hover:bg-action/90 focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50 disabled:pointer-events-none disabled:opacity-50"
            >
              {isLoading ? <Loader2 className="size-4 animate-spin" /> : <Send className="size-4" />}
            </button>
          </div>
          <MonoAnnotation className="truncate">{t('poweredBy.description')}</MonoAnnotation>
        </form>
      </main>

      <ContextPane
        className="hidden lg:flex"
        tools={toolCalls}
        sessionId={sessionId}
        requestId={messages.find((message) => message.requestId)?.requestId}
      />
    </div>
  );
}

/** The assistant's mark: the square the prototype puts beside every turn. */
function AssistantMark() {
  return (
    <span
      className="flex size-7 shrink-0 select-none items-center justify-center rounded-md bg-foreground text-background"
      aria-hidden="true"
    >
      <svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="1.8">
        <path d="M3 10.5 8 5l5 5.5" strokeLinecap="round" strokeLinejoin="round" />
        <circle cx="8" cy="12.5" r="1.4" fill="currentColor" stroke="none" />
      </svg>
    </span>
  );
}
