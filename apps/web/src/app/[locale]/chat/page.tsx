'use client';

import { useState, useRef, useEffect } from 'react';
import { Send, User, Bot, Loader2, Lightbulb, Sparkles, RefreshCw, Info } from 'lucide-react';
import { cn } from '@/lib/utils';
import { streamChatMessage, ApiError } from '@/lib/api';
import type { ChatResponse, EnhancedCitation, CitationStats } from '@/lib/types';
import CitationDisplay from '@/components/CitationDisplay';
import { useTranslations } from 'next-intl';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  sources?: ChatResponse['sources'];
  sourcesTruncated?: boolean;
  citationStats?: CitationStats | null;
  intermediateSteps?: ChatResponse['intermediate_steps'];
  isError?: boolean;
  requestId?: string;
}

// Suggested prompts for empty state
const SUGGESTED_PROMPTS = [
  'Find 2-bedroom apartments under $400,000 in Madrid',
  "What's the average price per square meter in Krakow?",
  'Compare properties in Warsaw city center',
  'Calculate mortgage for a $500,000 property with 20% down payment',
  'Show me houses with gardens in suburban areas',
];

export default function ChatPage() {
  const t = useTranslations('chat');

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

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const applyStreamError = (error: unknown, isRetry: boolean = false) => {
    let message = 'Unknown error';
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
        { message: userMessage, session_id: sid, include_intermediate_steps: debugMode },
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
        { message: lastUserMessage, session_id: sessionId, include_intermediate_steps: debugMode },
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
    <div className="container mx-auto max-w-4xl p-4 h-[calc(100vh-4rem)] flex flex-col">
      {/* The chat shows its title in the welcome panel only, so the route
          would lose its H1 as soon as the first message arrives. One heading
          stays in the document either way: visible in the welcome panel,
          hidden once the conversation starts. */}
      <h1 className="sr-only">{t('title')}</h1>
      {/* Messages Area - 4 Mandated States */}
      <div className="flex-1 overflow-y-auto space-y-4 p-4 rounded-lg border bg-card shadow-sm mb-4">
        {/* STATE 1: Empty state (zero-data) - before user starts */}
        {!hasStarted && messages.length === 0 && (
          <div
            className="flex flex-col items-center justify-center h-full min-h-[400px] text-center"
            role="status"
            aria-live="polite"
          >
            <div className="p-4 rounded-full bg-primary/10 mb-4">
              <Sparkles className="h-12 w-12 text-primary" aria-hidden="true" />
            </div>
            <div className="flex items-center gap-2 mb-2">
              <p className="text-2xl font-bold">{t('title')}</p>
              <span className="inline-flex items-center px-2 py-0.5 rounded-md bg-primary/10 text-primary text-xs font-medium border border-primary/20">
                {t('aiLabel')}
              </span>
            </div>
            <p className="text-muted-foreground max-w-md mb-6">{t('description')}</p>
            <div className="space-y-2 mb-6 text-left w-full max-w-md mx-auto">
              <p className="text-sm font-medium text-foreground flex items-center gap-2">
                <Lightbulb className="h-4 w-4" aria-hidden="true" />
                {t('emptyState.suggestions')}
              </p>
              <div className="flex flex-col gap-2">
                {SUGGESTED_PROMPTS.map((prompt, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => handleSuggestedPrompt(prompt)}
                    className="text-left text-sm text-primary hover:underline disabled:opacity-50 p-2 rounded-md hover:bg-muted/50 transition-colors"
                    disabled={isLoading}
                  >
                    &ldquo;{prompt}&rdquo;
                  </button>
                ))}
              </div>
            </div>
            <div className="text-xs text-muted-foreground max-w-md">
              <p className="font-medium mb-1">{t('poweredBy.title')}</p>
              <p>{t('poweredBy.description')}</p>
            </div>
          </div>
        )}

        {/* STATE 2: Loading state (streaming) - thinking indicator */}
        {isLoading && (
          <div
            className="flex w-full items-start gap-4 p-4 rounded-lg bg-background border"
            role="status"
            aria-live="polite"
            aria-label={t('loading.thinking')}
          >
            <div className="flex h-8 w-8 shrink-0 select-none items-center justify-center rounded-md border shadow bg-primary text-primary-foreground">
              <Bot className="h-4 w-4" />
            </div>
            <div className="flex-1 flex items-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
              <span className="text-sm text-muted-foreground">{t('loading.thinking')}</span>
            </div>
          </div>
        )}

        {/* STATE 3 & 4: Message list (Populated state + inline errors) */}
        {messages.map((message, index) => (
          <div
            key={index}
            className={cn(
              'flex w-full items-start gap-4 p-4 rounded-lg',
              message.role === 'user'
                ? 'bg-muted/50'
                : message.isError
                  ? 'bg-destructive/10 border border-destructive/20'
                  : 'bg-background border'
            )}
            role={message.role === 'assistant' && message.isError ? 'alert' : undefined}
            aria-live={message.isError ? 'assertive' : 'polite'}
          >
            <div
              className={cn(
                'flex h-8 w-8 shrink-0 select-none items-center justify-center rounded-md border shadow',
                message.role === 'user' ? 'bg-background' : 'bg-primary text-primary-foreground'
              )}
            >
              {message.role === 'user' ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
            </div>
            <div className="flex-1 space-y-2 overflow-hidden">
              {/* AI Disclosure Badge - shown for assistant messages (EU AI Act compliance) */}
              {message.role === 'assistant' && message.content && !message.isError && (
                <div className="flex items-start gap-2 text-xs text-muted-foreground">
                  <Info className="h-3 w-3 mt-0.5 flex-shrink-0" aria-hidden="true" />
                  <p>{t('aiDisclaimer')}</p>
                </div>
              )}

              <div className="prose break-words dark:prose-invert text-sm leading-relaxed">
                {!message.content ? (
                  <span className="text-muted-foreground italic">{t('loading.thinking')}</span>
                ) : (
                  message.content
                )}
              </div>

              {/* Sources display */}
              {message.role === 'assistant' && message.sources && message.sources.length > 0 && (
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
                message.role === 'assistant' &&
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
                    <div className="text-xs text-muted-foreground font-mono">
                      {t('retry.requestId', { id: message.requestId })}
                    </div>
                  )}
                  <button
                    type="button"
                    onClick={handleRetry}
                    disabled={isLoading}
                    className="inline-flex items-center gap-2 rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground shadow hover:bg-primary/90 focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50 disabled:opacity-50"
                  >
                    <RefreshCw className="h-3 w-3" />
                    {t('retry.button')}
                  </button>
                </div>
              )}
            </div>
          </div>
        ))}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Form */}
      <form ref={formRef} onSubmit={handleSubmit} className="flex gap-4">
        <input
          data-testid="chat-input"
          className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50 disabled:cursor-not-allowed disabled:opacity-50"
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
          className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow hover:bg-primary/90 focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50 disabled:pointer-events-none disabled:opacity-50 w-12"
        >
          {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
        </button>
      </form>
    </div>
  );
}
