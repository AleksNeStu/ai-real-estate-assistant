'use client';

import { useState } from 'react';
import {
  FileUp,
  Loader2,
  MessageSquareText,
  Trash2,
  Upload,
  AlertCircle,
  FileText,
  Sparkles,
  Database,
} from 'lucide-react';
import { useTranslations } from 'next-intl';
import { ragQa, resetRagKnowledge, uploadRagDocuments, ApiError } from '@/lib/api';
import type { RagQaResponse, RagResetResponse, RagUploadResponse } from '@/lib/types';
import { PageHeader } from '@/components/ui/page-header';

interface ErrorState {
  message: string;
  requestId?: string;
}

export default function KnowledgePage() {
  const t = useTranslations('pages.knowledge');
  const tError = useTranslations('error');
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<ErrorState | null>(null);
  const [uploadResult, setUploadResult] = useState<RagUploadResponse | null>(null);

  const [resetting, setResetting] = useState(false);
  const [resetError, setResetError] = useState<ErrorState | null>(null);
  const [resetResult, setResetResult] = useState<RagResetResponse | null>(null);

  const [question, setQuestion] = useState<string>('');
  const [topK, setTopK] = useState<string>('5');
  const [provider, setProvider] = useState<string>('');
  const [model, setModel] = useState<string>('');
  const [asking, setAsking] = useState(false);
  const [qaError, setQaError] = useState<ErrorState | null>(null);
  const [qaResult, setQaResult] = useState<RagQaResponse | null>(null);

  const parseTopK = (): number => {
    const raw = topK.trim();
    if (!raw) return 5;
    const n = Number(raw);
    if (!Number.isFinite(n)) return 5;
    const asInt = Math.floor(n);
    if (asInt < 1) return 1;
    if (asInt > 50) return 50;
    return asInt;
  };

  const extractErrorState = (err: unknown): ErrorState => {
    let message = tError('generic');
    let requestId: string | undefined = undefined;

    if (err instanceof ApiError) {
      message = err.message;
      requestId = err.request_id;
    } else if (err instanceof Error) {
      message = err.message;
    } else {
      message = String(err);
    }

    return { message, requestId };
  };

  const onUpload = async () => {
    setUploadError(null);
    setUploadResult(null);
    if (!files.length) {
      setUploadError({ message: t('upload.selectFile') });
      return;
    }
    setUploading(true);
    try {
      const res = await uploadRagDocuments(files);
      setUploadResult(res);
    } catch (e: unknown) {
      setUploadError(extractErrorState(e));
    } finally {
      setUploading(false);
    }
  };

  const onResetKnowledge = async () => {
    setResetError(null);
    setResetResult(null);

    const confirmed = window.confirm(t('manage.confirm'));
    if (!confirmed) return;

    setResetting(true);
    try {
      const res = await resetRagKnowledge();
      setResetResult(res);
      setUploadResult(null);
      setQaResult(null);
      setQaError(null);
    } catch (e: unknown) {
      setResetError(extractErrorState(e));
    } finally {
      setResetting(false);
    }
  };

  const onAsk = async () => {
    setQaError(null);
    setQaResult(null);
    const q = question.trim();
    if (!q) {
      setQaError({ message: t('ask.enterQuestion') });
      return;
    }
    setAsking(true);
    try {
      const res = await ragQa({
        question: q,
        top_k: parseTopK(),
        provider: provider.trim() || undefined,
        model: model.trim() || undefined,
      });
      setQaResult(res);
    } catch (e: unknown) {
      setQaError(extractErrorState(e));
    } finally {
      setAsking(false);
    }
  };

  return (
    <div className="container mx-auto max-w-5xl px-4 py-8">
      <PageHeader className="mb-8" title={t('title')} description={t('description')} />

      <div className="grid gap-8">
        {/* Upload Section - 4 Mandated States */}
        <section className="border rounded-lg p-6">
          <div className="flex items-center gap-2 mb-4">
            <Upload className="w-5 h-5" />
            <h2 className="text-xl font-semibold">{t('upload.title')}</h2>
          </div>

          {/* Empty/Loading/Error/Populated states for upload */}
          <input
            className="border p-2 w-full"
            type="file"
            multiple
            accept=".txt,.md,.pdf,.docx"
            onChange={(e) => {
              const list = e.target.files ? Array.from(e.target.files) : [];
              setFiles(list);
            }}
            aria-label={t('upload.filesAria')}
            disabled={uploading}
          />

          {files.length ? (
            <ul className="text-sm text-muted-foreground mt-2 list-disc pl-5">
              {files.map((f) => (
                <li key={`${f.name}-${f.size}`}>{f.name}</li>
              ))}
            </ul>
          ) : null}

          <div className="mt-4 flex items-center gap-3">
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow hover:bg-primary/90 disabled:opacity-50 focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
              disabled={uploading || !files.length}
              onClick={onUpload}
            >
              {uploading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  {t('upload.uploading')}
                </>
              ) : (
                <>
                  <FileUp className="w-4 h-4" />
                  {t('upload.upload')}
                </>
              )}
            </button>
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-md border px-4 py-2 text-sm font-medium hover:bg-muted disabled:opacity-50 focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
              disabled={uploading || !files.length}
              onClick={() => {
                setFiles([]);
                setUploadError(null);
                setUploadResult(null);
              }}
            >
              {t('upload.clear')}
            </button>
          </div>

          {/* Upload Loading State */}
          {uploading && (
            <div
              className="mt-4 p-4 rounded-lg border bg-muted/30 text-center"
              role="status"
              aria-live="polite"
            >
              <Loader2 className="w-5 h-5 animate-spin mx-auto mb-2 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">{t('upload.processing')}</p>
            </div>
          )}

          {/* Upload Error State */}
          {uploadError && (
            <div
              className="mt-4 p-4 rounded-lg bg-destructive/10 border border-destructive/20"
              role="alert"
              aria-live="assertive"
            >
              <div className="flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-destructive flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-destructive mb-1">{t('upload.failed')}</p>
                  <p className="text-sm text-destructive/90">{uploadError.message}</p>
                  {uploadError.requestId && (
                    <p className="text-xs text-muted-foreground mt-2 font-mono">
                      request_id={uploadError.requestId}
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Upload Populated State */}
          {uploadResult ? (
            <div className="mt-4 p-4 rounded-lg bg-success/15 border border-chart-7/30">
              <p className="font-medium text-success">{uploadResult.message}</p>
              <p className="text-sm text-success">
                {t('upload.chunksIndexed', { count: uploadResult.chunks_indexed })}
              </p>
              {uploadResult.errors.length ? (
                <ul className="mt-2 text-sm text-warning list-disc pl-5">
                  {uploadResult.errors.map((err, idx) => (
                    <li key={idx}>{err}</li>
                  ))}
                </ul>
              ) : null}
            </div>
          ) : null}

          {/* Knowledge Management Section */}
          <div className="mt-6 pt-6 border-t">
            <div className="flex items-center gap-2 mb-3">
              <Database className="w-4 h-4" />
              <p className="font-medium">{t('manage.title')}</p>
            </div>
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-md border px-4 py-2 text-sm font-medium hover:bg-muted disabled:opacity-50 focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
              disabled={resetting}
              onClick={onResetKnowledge}
            >
              {resetting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  {t('manage.clearing')}
                </>
              ) : (
                <>
                  <Trash2 className="w-4 h-4" />
                  {t('manage.clear')}
                </>
              )}
            </button>

            {/* Reset Error State */}
            {resetError && (
              <div className="mt-3 flex items-center gap-3" role="alert" aria-live="assertive">
                <AlertCircle className="w-5 h-5 text-destructive flex-shrink-0" />
                <span className="text-sm text-destructive">{resetError.message}</span>
                {resetError.requestId && (
                  <span className="text-xs text-muted-foreground font-mono">
                    (request_id={resetError.requestId})
                  </span>
                )}
              </div>
            )}

            {/* Reset Populated State */}
            {resetResult ? (
              <div className="mt-3">
                <p className="text-sm text-muted-foreground">
                  {t('manage.result', {
                    message: resetResult.message,
                    removed: resetResult.documents_removed,
                    remaining: resetResult.documents_remaining,
                  })}
                </p>
              </div>
            ) : null}
          </div>
        </section>

        {/* Q&A Section - 4 Mandated States */}
        <section className="border rounded-lg p-6">
          <div className="flex items-center gap-2 mb-4">
            <MessageSquareText className="w-5 h-5" />
            <h2 className="text-xl font-semibold">{t('ask.title')}</h2>
          </div>

          {/* Empty state - prompt user to ask */}
          {!qaResult && !qaError && !asking && (
            <div
              className="flex flex-col items-center justify-center py-8 text-center border rounded-lg border-dashed bg-muted/20 mb-4"
              role="status"
              aria-live="polite"
            >
              <FileText className="h-8 w-8 text-muted-foreground mb-2" aria-hidden="true" />
              <p className="text-sm text-muted-foreground max-w-sm mx-auto">{t('ask.empty')}</p>
            </div>
          )}

          <textarea
            className="border p-2 w-full resize-none"
            placeholder={t('ask.placeholder')}
            rows={3}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            aria-label={t('ask.questionAria')}
            disabled={asking}
          />

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-3">
            <input
              className="border p-2 w-full"
              type="number"
              min={1}
              max={50}
              value={topK}
              onChange={(e) => setTopK(e.target.value)}
              aria-label={t('ask.topKAria')}
              placeholder={t('ask.topKPlaceholder')}
              disabled={asking}
            />
            <input
              className="border p-2 w-full"
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              aria-label={t('ask.providerAria')}
              placeholder={t('ask.providerPlaceholder')}
              disabled={asking}
            />
            <input
              className="border p-2 w-full"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              aria-label={t('ask.modelAria')}
              placeholder={t('ask.modelPlaceholder')}
              disabled={asking}
            />
          </div>

          <div className="mt-4 flex items-center gap-3">
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow hover:bg-primary/90 disabled:opacity-50 focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
              disabled={asking || !question.trim()}
              onClick={onAsk}
            >
              {asking ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  {t('ask.asking')}
                </>
              ) : (
                <>
                  <MessageSquareText className="w-4 h-4" />
                  {t('ask.ask')}
                </>
              )}
            </button>
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-md border px-4 py-2 text-sm font-medium hover:bg-muted disabled:opacity-50 focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
              disabled={asking || (!question.trim() && !qaResult && !qaError)}
              onClick={() => {
                setQuestion('');
                setQaError(null);
                setQaResult(null);
              }}
            >
              {t('ask.clear')}
            </button>
          </div>

          {/* Asking Loading State */}
          {asking && (
            <div
              className="mt-4 p-4 rounded-lg border bg-muted/30 text-center"
              role="status"
              aria-live="polite"
            >
              <Loader2 className="w-5 h-5 animate-spin mx-auto mb-2 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">{t('ask.searching')}</p>
            </div>
          )}

          {/* QA Error State */}
          {qaError && (
            <div
              className="mt-4 p-4 rounded-lg bg-destructive/10 border border-destructive/20"
              role="alert"
              aria-live="assertive"
            >
              <div className="flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-destructive flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-destructive mb-1">{t('ask.failed')}</p>
                  <p className="text-sm text-destructive/90">{qaError.message}</p>
                  {qaError.requestId && (
                    <p className="text-xs text-muted-foreground mt-2 font-mono">
                      request_id={qaError.requestId}
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* QA Populated State */}
          {qaResult && (
            <div className="mt-4 space-y-4">
              <div className="border rounded p-4 bg-muted/30">
                <p className="text-xs text-muted-foreground mb-2 font-mono">
                  llm_used={String(qaResult.llm_used)} provider={qaResult.provider ?? 'null'} model=
                  {qaResult.model ?? 'null'}
                </p>
                <p className="whitespace-pre-wrap text-sm leading-relaxed">{qaResult.answer}</p>
              </div>

              <div>
                <h3 className="font-semibold text-sm mb-2">{t('ask.citations')}</h3>
                {qaResult.citations.length ? (
                  <ul className="text-sm text-muted-foreground list-disc pl-5 space-y-1">
                    {qaResult.citations.map((c, idx) => (
                      <li key={`${c.source}-${c.chunk_index}-${idx}`}>
                        {t('ask.citationItem', {
                          source: c.source ?? '',
                          chunk: c.chunk_index ?? 0,
                        })}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-muted-foreground">{t('ask.noCitations')}</p>
                )}
              </div>
            </div>
          )}
        </section>
      </div>

      {/* Empty State Guidance - When no data and no operations */}
      {!uploadResult &&
        !resetResult &&
        !qaResult &&
        !uploadError &&
        !resetError &&
        !qaError &&
        !uploading &&
        !resetting &&
        !asking && (
          <div
            className="mt-8 p-6 rounded-lg border bg-muted/20 text-center"
            role="status"
            aria-live="polite"
          >
            <Sparkles className="h-10 w-10 text-muted-foreground mx-auto mb-3" aria-hidden="true" />
            <h3 className="text-base font-semibold text-foreground mb-2">{t('empty.title')}</h3>
            <div className="text-sm text-muted-foreground max-w-md mx-auto space-y-2">
              <p>{t('empty.upload')}</p>
              <p>{t('empty.then')}</p>
              <p className="text-xs">{t('empty.providers')}</p>
            </div>
          </div>
        )}
    </div>
  );
}
