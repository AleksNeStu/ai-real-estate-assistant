"use client";

import { useState } from "react";
import { FileUp, Loader2, MessageSquareText, Trash2, Upload, AlertCircle, FileText, Sparkles, Database } from "lucide-react";
import { useTranslations } from "next-intl";
import { ragQa, resetRagKnowledge, uploadRagDocuments, ApiError } from "@/lib/api";
import type { RagQaResponse, RagResetResponse, RagUploadResponse } from "@/lib/types";
import { PageHeader } from "@/components/ui/page-header";

interface ErrorState {
  message: string;
  requestId?: string;
}

export default function KnowledgePage() {
  const t = useTranslations("pages.knowledge");
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<ErrorState | null>(null);
  const [uploadResult, setUploadResult] = useState<RagUploadResponse | null>(null);

  const [resetting, setResetting] = useState(false);
  const [resetError, setResetError] = useState<ErrorState | null>(null);
  const [resetResult, setResetResult] = useState<RagResetResponse | null>(null);

  const [question, setQuestion] = useState<string>("");
  const [topK, setTopK] = useState<string>("5");
  const [provider, setProvider] = useState<string>("");
  const [model, setModel] = useState<string>("");
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
    let message = "Unknown error";
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
      setUploadError({ message: "Select at least one file to upload." });
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

    const confirmed = window.confirm("Clear all indexed knowledge documents? This cannot be undone.");
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
      setQaError({ message: "Enter a question." });
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
      <PageHeader
        className="mb-8"
        title={t('title')}
        description={t('description')}
      />

      <div className="grid gap-8">
        {/* Upload Section - 4 Mandated States */}
        <section className="border rounded-lg p-6">
          <div className="flex items-center gap-2 mb-4">
            <Upload className="w-5 h-5" />
            <h2 className="text-xl font-semibold">Upload Documents</h2>
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
            aria-label="Knowledge files"
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
            <button type="button"
              className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow hover:bg-primary/90 disabled:opacity-50 focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
              disabled={uploading || !files.length}
              onClick={onUpload}
            >
              {uploading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Uploading...
                </>
              ) : (
                <>
                  <FileUp className="w-4 h-4" />
                  Upload
                </>
              )}
            </button>
            <button type="button"
              className="inline-flex items-center gap-2 rounded-md border px-4 py-2 text-sm font-medium hover:bg-muted disabled:opacity-50 focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
              disabled={uploading || !files.length}
              onClick={() => {
                setFiles([]);
                setUploadError(null);
                setUploadResult(null);
              }}
            >
              Clear
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
              <p className="text-sm text-muted-foreground">Uploading and processing documents...</p>
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
                  <p className="text-sm font-medium text-destructive mb-1">Upload Failed</p>
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
              <p className="text-sm text-success">Chunks indexed: {uploadResult.chunks_indexed}</p>
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
              <p className="font-medium">Manage Knowledge Base</p>
            </div>
            <button type="button"
              className="inline-flex items-center gap-2 rounded-md border px-4 py-2 text-sm font-medium hover:bg-muted disabled:opacity-50 focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
              disabled={resetting}
              onClick={onResetKnowledge}
            >
              {resetting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Clearing...
                </>
              ) : (
                <>
                  <Trash2 className="w-4 h-4" />
                  Clear Knowledge
                </>
              )}
            </button>

            {/* Reset Error State */}
            {resetError && (
              <div
                  className="mt-3 flex items-center gap-3"
                  role="alert"
                  aria-live="assertive"
              >
                <AlertCircle className="w-4 h-4 text-destructive flex-shrink-0" />
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
                  {resetResult.message}. Removed {resetResult.documents_removed}. Remaining {resetResult.documents_remaining}.
                </p>
              </div>
            ) : null}
          </div>
        </section>

        {/* Q&A Section - 4 Mandated States */}
        <section className="border rounded-lg p-6">
          <div className="flex items-center gap-2 mb-4">
            <MessageSquareText className="w-5 h-5" />
            <h2 className="text-xl font-semibold">Ask Questions</h2>
          </div>

          {/* Empty state - prompt user to ask */}
          {!qaResult && !qaError && !asking && (
            <div
              className="flex flex-col items-center justify-center py-8 text-center border rounded-lg border-dashed bg-muted/20 mb-4"
              role="status"
              aria-live="polite"
            >
              <FileText className="h-8 w-8 text-muted-foreground mb-2" aria-hidden="true" />
              <p className="text-sm text-muted-foreground max-w-sm mx-auto">
                Upload documents and ask questions to get answers with citations from your knowledge base.
              </p>
            </div>
          )}

          <textarea
            className="border p-2 w-full resize-none"
            placeholder="Ask a question about your uploaded documents..."
            rows={3}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            aria-label="Knowledge question"
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
              aria-label="Top K"
              placeholder="Top K (1-50)"
              disabled={asking}
            />
            <input
              className="border p-2 w-full"
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              aria-label="Provider override"
              placeholder="Provider (optional)"
              disabled={asking}
            />
            <input
              className="border p-2 w-full"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              aria-label="Model override"
              placeholder="Model (optional)"
              disabled={asking}
            />
          </div>

          <div className="mt-4 flex items-center gap-3">
            <button type="button"
              className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow hover:bg-primary/90 disabled:opacity-50 focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
              disabled={asking || !question.trim()}
              onClick={onAsk}
            >
              {asking ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Asking...
                </>
              ) : (
                <>
                  <MessageSquareText className="w-4 h-4" />
                  Ask
                </>
              )}
            </button>
            <button type="button"
              className="inline-flex items-center gap-2 rounded-md border px-4 py-2 text-sm font-medium hover:bg-muted disabled:opacity-50 focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
              disabled={asking || (!question.trim() && !qaResult && !qaError)}
              onClick={() => {
                setQuestion("");
                setQaError(null);
                setQaResult(null);
              }}
            >
              Clear
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
              <p className="text-sm text-muted-foreground">Searching knowledge base...</p>
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
                  <p className="text-sm font-medium text-destructive mb-1">Question Failed</p>
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
                  llm_used={String(qaResult.llm_used)} provider={qaResult.provider ?? "null"} model={qaResult.model ?? "null"}
                </p>
                <p className="whitespace-pre-wrap text-sm leading-relaxed">{qaResult.answer}</p>
              </div>

              <div>
                <h3 className="font-semibold text-sm mb-2">Citations</h3>
                {qaResult.citations.length ? (
                  <ul className="text-sm text-muted-foreground list-disc pl-5 space-y-1">
                    {qaResult.citations.map((c, idx) => (
                      <li key={`${c.source}-${c.chunk_index}-${idx}`}>
                        {c.source} (chunk {c.chunk_index})
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-muted-foreground">No citations returned.</p>
                )}
              </div>
            </div>
          )}
        </section>
      </div>

      {/* Empty State Guidance - When no data and no operations */}
      {!uploadResult && !resetResult && !qaResult && !uploadError && !resetError && !qaError && !uploading && !resetting && !asking && (
        <div
          className="mt-8 p-6 rounded-lg border bg-muted/20 text-center"
          role="status"
          aria-live="polite"
        >
          <Sparkles className="h-10 w-10 text-muted-foreground mx-auto mb-3" aria-hidden="true" />
          <h3 className="text-base font-semibold text-foreground mb-2">Get Started with Knowledge</h3>
          <div className="text-sm text-muted-foreground max-w-md mx-auto space-y-2">
            <p>Upload documents (PDF, TXT, MD, DOCX) to build your local knowledge base.</p>
            <p>Then ask questions and get answers with source citations.</p>
            <p className="text-xs">Supported providers: OpenAI, Anthropic, Google, Grok, DeepSeek, and Ollama (local).</p>
          </div>
        </div>
      )}
    </div>
  );
}
