'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import { Loader2, MessageSquareText, Trash2, Upload } from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';

import { Button } from '@/components/ui/button';
import { EmptyState, ErrorState } from '@/components/ui/states';
import { MonoAnnotation } from '@/components/ui/mono-annotation';
import { PageHeader } from '@/components/ui/page-header';
import { DocumentLedger } from '@/components/knowledge/document-ledger';
import { PassageLedger } from '@/components/knowledge/passage-ledger';
import { ragQa, resetRagKnowledge, uploadRagDocuments, ApiError } from '@/lib/api';
import type { RagQaResponse, RagResetResponse, RagUploadResponse } from '@/lib/types';

interface ErrorStateValue {
  message: string;
  requestId?: string;
}

const TOP_K_MIN = 1;
const TOP_K_MAX = 50;
const TOP_K_DEFAULT = 5;

export default function KnowledgePage() {
  const t = useTranslations('pages.knowledge');
  const tError = useTranslations('error');
  const locale = useLocale();

  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<ErrorStateValue | null>(null);
  const [uploadResult, setUploadResult] = useState<RagUploadResponse | null>(null);
  /** The chunks the uploads of this session wrote. */
  const [chunksIndexed, setChunksIndexed] = useState(0);

  const [resetting, setResetting] = useState(false);
  const [resetError, setResetError] = useState<ErrorStateValue | null>(null);
  const [resetResult, setResetResult] = useState<RagResetResponse | null>(null);

  const [question, setQuestion] = useState<string>('');
  const [topK, setTopK] = useState<string>(String(TOP_K_DEFAULT));
  const [provider, setProvider] = useState<string>('');
  const [model, setModel] = useState<string>('');
  const [asking, setAsking] = useState(false);
  const [qaError, setQaError] = useState<ErrorStateValue | null>(null);
  const [qaResult, setQaResult] = useState<RagQaResponse | null>(null);

  const parseTopK = (): number => {
    const raw = topK.trim();
    if (!raw) return TOP_K_DEFAULT;
    const n = Number(raw);
    if (!Number.isFinite(n)) return TOP_K_DEFAULT;
    const asInt = Math.floor(n);
    if (asInt < TOP_K_MIN) return TOP_K_MIN;
    if (asInt > TOP_K_MAX) return TOP_K_MAX;
    return asInt;
  };

  const topKValue = parseTopK();

  const extractErrorState = (err: unknown): ErrorStateValue => {
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
      setChunksIndexed((total) => total + res.chunks_indexed);
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
      setChunksIndexed(0);
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
        top_k: topKValue,
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

  const citationList = qaResult?.citations ?? [];
  const answered = Boolean(qaResult);
  const resolvedProvider = qaResult?.provider ?? null;
  const resolvedModel = qaResult?.model ?? null;

  const answerNote = useMemo(() => {
    if (!qaResult) return null;
    if (!qaResult.llm_used) return t('ask.noteExtracted');
    return t('ask.noteAi', {
      provider: resolvedProvider ?? t('ask.unknownModel'),
      model: resolvedModel ?? t('ask.unknownModel'),
    });
  }, [qaResult, resolvedProvider, resolvedModel, t]);

  return (
    <div className="flex min-h-[calc(100vh-56px)] flex-col">
      <div className="border-b border-border px-6 pb-5 pt-6">
        <PageHeader
          title={t('title')}
          description={t('description')}
          actions={<MonoAnnotation>{t('source')}</MonoAnnotation>}
        />
      </div>

      <div className="grid flex-1 lg:grid-cols-[420px_minmax(0,1fr)]">
        <aside className="flex flex-col gap-5 border-b border-border px-6 py-5 lg:border-b-0 lg:border-r">
          <label
            onDragOver={(event) => event.preventDefault()}
            onDrop={(event) => {
              event.preventDefault();
              const dropped = event.dataTransfer?.files
                ? Array.from(event.dataTransfer.files)
                : [];
              if (dropped.length) setFiles(dropped);
            }}
            className="flex h-[120px] cursor-pointer flex-col items-center justify-center gap-1 rounded-lg border border-dashed border-muted-foreground bg-muted/40 px-4 text-center hover:bg-muted"
          >
            <span className="text-[14px] font-medium text-foreground">
              {t('upload.dropLabel')}
            </span>
            <span className="text-[12px] text-muted-foreground">{t('upload.formats')}</span>
            <input
              type="file"
              multiple
              accept=".txt,.md,.pdf,.docx"
              className="sr-only"
              aria-label={t('upload.filesAria')}
              onChange={(event) => {
                const list = event.target.files ? Array.from(event.target.files) : [];
                setFiles(list);
              }}
              disabled={uploading}
            />
          </label>

          <Button onClick={onUpload} disabled={uploading || !files.length} className="w-full">
            {uploading ? (
              <>
                <Loader2 className="size-4 animate-spin" aria-hidden />
                {t('upload.uploading')}
              </>
            ) : (
              <>
                <Upload className="size-4" aria-hidden />
                {t('upload.upload')}
              </>
            )}
          </Button>

          {uploading ? (
            <p className="text-[12px] text-muted-foreground" role="status">
              {t('upload.processing')}
            </p>
          ) : null}

          {uploadError ? (
            <ErrorState
              title={t('upload.failed')}
              description={uploadError.message}
              action={
                uploadError.requestId ? (
                  <MonoAnnotation>request_id={uploadError.requestId}</MonoAnnotation>
                ) : null
              }
            />
          ) : null}

          {uploadResult ? (
            <div className="flex flex-col gap-1 border-t border-foreground pt-2.5">
              <p className="text-[13px] font-medium text-success">{uploadResult.message}</p>
              <p className="text-[12px] text-muted-foreground">
                {t('upload.chunksIndexed', { count: uploadResult.chunks_indexed })}
              </p>
              {uploadResult.errors.length ? (
                <ul className="mt-1 list-disc pl-4 text-[12px] text-warning">
                  {uploadResult.errors.map((error, index) => (
                    <li key={index}>{error}</li>
                  ))}
                </ul>
              ) : null}
            </div>
          ) : null}

          <DocumentLedger
            files={files.map((file) => ({
              name: file.name,
              size: file.size,
              type: file.type,
            }))}
            chunksIndexed={chunksIndexed}
            documentsRemaining={resetResult ? resetResult.documents_remaining : null}
            onRemove={(index) =>
              setFiles((current) => current.filter((_, position) => position !== index))
            }
          />

          <div className="flex flex-col gap-2 border-t border-border pt-4">
            <Button
              variant="outline"
              onClick={onResetKnowledge}
              disabled={resetting}
              className="self-start"
            >
              {resetting ? (
                <>
                  <Loader2 className="size-4 animate-spin" aria-hidden />
                  {t('manage.clearing')}
                </>
              ) : (
                <>
                  <Trash2 className="size-4" aria-hidden />
                  {t('manage.clear')}
                </>
              )}
            </Button>

            {resetError ? (
              <ErrorState
                title={t('manage.failed')}
                description={resetError.message}
                action={
                  resetError.requestId ? (
                    <MonoAnnotation>request_id={resetError.requestId}</MonoAnnotation>
                  ) : null
                }
              />
            ) : null}

            {resetResult ? (
              <p className="text-[12px] text-muted-foreground">
                {t('manage.result', {
                  message: resetResult.message,
                  removed: resetResult.documents_removed,
                  remaining: resetResult.documents_remaining,
                })}
              </p>
            ) : null}

            <p className="text-[12px] leading-4 text-muted-foreground">{t('manage.note')}</p>
          </div>
        </aside>

        <main className="flex min-w-0 flex-col gap-5 px-6 py-5 lg:px-8">
          <form
            onSubmit={(event) => {
              event.preventDefault();
              void onAsk();
            }}
            className="flex flex-col gap-3"
          >
            <div className="flex gap-2">
              <input
                type="text"
                className="h-11 min-w-0 flex-1 rounded-lg border border-input bg-background px-3.5 text-[15px] text-foreground outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
                placeholder={t('ask.placeholder')}
                aria-label={t('ask.questionAria')}
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                disabled={asking}
              />
              <Button
                type="submit"
                className="h-11 shrink-0"
                disabled={asking || !question.trim()}
                data-testid="knowledge-ask"
              >
                {asking ? (
                  <>
                    <Loader2 className="size-4 animate-spin" aria-hidden />
                    {t('ask.asking')}
                  </>
                ) : (
                  <>
                    <MessageSquareText className="size-4" aria-hidden />
                    {t('ask.ask')}
                  </>
                )}
              </Button>
            </div>

            <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-[12px] text-muted-foreground">
              <label className="flex items-center gap-2">
                <span>{t('ask.topKLabel')}</span>
                <input
                  type="range"
                  min={TOP_K_MIN}
                  max={TOP_K_MAX}
                  value={topK}
                  aria-label={t('ask.topKAria')}
                  onChange={(event) => setTopK(event.target.value)}
                  disabled={asking}
                  className="w-[100px] accent-foreground"
                />
                <span className="font-mono text-[12px] font-medium text-foreground">
                  {topKValue}
                </span>
              </label>

              <label className="flex items-center gap-2">
                <span>{t('ask.providerLabel')}</span>
                <input
                  type="text"
                  value={provider}
                  aria-label={t('ask.providerAria')}
                  placeholder={t('ask.providerPlaceholder')}
                  onChange={(event) => setProvider(event.target.value)}
                  disabled={asking}
                  className="h-6 w-[130px] rounded-sm border border-border bg-background px-2 font-mono text-[12px] text-foreground outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
                />
              </label>

              <label className="flex items-center gap-2">
                <span>{t('ask.modelLabel')}</span>
                <input
                  type="text"
                  value={model}
                  aria-label={t('ask.modelAria')}
                  placeholder={t('ask.modelPlaceholder')}
                  onChange={(event) => setModel(event.target.value)}
                  disabled={asking}
                  className="h-6 w-[130px] rounded-sm border border-border bg-background px-2 font-mono text-[12px] text-foreground outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
                />
              </label>

              <Link
                href={`/${locale}/settings`}
                className="ml-auto text-[12px] text-foreground hover:underline"
              >
                {t('ask.otherProviders')}
              </Link>
            </div>
          </form>

          {asking ? (
            <p className="text-[12px] text-muted-foreground" role="status">
              {t('ask.searching')}
            </p>
          ) : null}

          {qaError ? (
            <ErrorState
              title={t('ask.failed')}
              description={qaError.message}
              action={
                qaError.requestId ? (
                  <MonoAnnotation>request_id={qaError.requestId}</MonoAnnotation>
                ) : null
              }
            />
          ) : null}

          {answered && qaResult ? (
            <div className="flex flex-col gap-4">
              <p className="whitespace-pre-wrap text-[15px] leading-6 text-foreground">
                {qaResult.answer}
              </p>

              {citationList.length ? (
                <PassageLedger citations={citationList} topK={topKValue} />
              ) : (
                <p className="text-[12px] text-muted-foreground">{t('ask.noCitations')}</p>
              )}

              <p className="text-[12px] leading-4 text-muted-foreground">{answerNote}</p>
            </div>
          ) : null}

          {!answered && !qaError && !asking ? (
            <EmptyState title={t('ask.emptyTitle')} description={t('ask.empty')} />
          ) : null}
        </main>
      </div>
    </div>
  );
}
