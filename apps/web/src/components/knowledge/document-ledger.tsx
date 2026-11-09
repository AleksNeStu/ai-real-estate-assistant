'use client';

import { useTranslations } from 'next-intl';

import { MonoAnnotation } from '@/components/ui/mono-annotation';

/**
 * The files the reader picked, and the state of the index.
 *
 * The design draws the sidebar as a ledger: a rule, then a row per file.
 *
 * The API cannot list what is indexed - `rag/upload` answers with the number
 * of chunks it wrote and `rag/reset` with the number of documents that are
 * left, and there is no endpoint that returns the documents themselves. So
 * the ledger below is honest about what it is: the files that are waiting to
 * be uploaded, and the two numbers the index reports. A row per indexed
 * document would have to be invented, and nothing here is.
 */

export interface KnowledgeFile {
  name: string;
  size: number;
  type: string;
}

export interface DocumentLedgerProps {
  files: KnowledgeFile[];
  /** The chunks the uploads of this session wrote. */
  chunksIndexed: number;
  /** The documents the index reported after the last clear. Null before that. */
  documentsRemaining: number | null;
  /** Removes a file from the selection. */
  onRemove: (index: number) => void;
  className?: string;
}

/** A file size in the unit a reader thinks in. */
function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} kB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/** The extension of a file name, in the mono voice the design wants for it. */
function fileKind(name: string): string {
  const dot = name.lastIndexOf('.');
  if (dot < 0 || dot === name.length - 1) return 'file';
  return name.slice(dot + 1).toLowerCase();
}

export function DocumentLedger({
  files,
  chunksIndexed,
  documentsRemaining,
  onRemove,
  className,
}: DocumentLedgerProps) {
  const t = useTranslations('pages.knowledge');

  return (
    <div className={className}>
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-[14px] font-semibold text-foreground">
          {t('documents.title')}
        </span>
        <MonoAnnotation>{t('documents.fileCount', { count: files.length })}</MonoAnnotation>
      </div>

      <div className="mt-2 border-t border-border">
        {files.length === 0 ? (
          <p className="py-3 text-[12px] leading-4 text-muted-foreground">
            {t('documents.empty')}
          </p>
        ) : (
          files.map((file, index) => (
            <div
              key={`${file.name}-${index}`}
              className="grid grid-cols-[minmax(0,1fr)_auto] items-baseline gap-x-3 gap-y-1 border-b border-border py-2.5"
            >
              <span className="truncate text-[14px] font-medium leading-5 text-foreground">
                {file.name}
              </span>
              <MonoAnnotation className="shrink-0">
                {fileKind(file.name)} · {formatSize(file.size)}
              </MonoAnnotation>
              <span className="col-span-2 text-[12px] leading-4 text-muted-foreground">
                {t('documents.pending')}
              </span>
              <button
                type="button"
                onClick={() => onRemove(index)}
                className="col-span-2 justify-self-start text-[12px] text-muted-foreground hover:text-foreground hover:underline"
              >
                {t('documents.remove')}
              </button>
            </div>
          ))
        )}
      </div>

      <div className="mt-4 flex flex-col gap-1.5 border-t border-foreground pt-2.5">
        <div className="flex items-baseline justify-between gap-3">
          <span className="text-[12px] leading-4 text-muted-foreground">
            {t('documents.chunksIndexed')}
          </span>
          <MonoAnnotation>{chunksIndexed}</MonoAnnotation>
        </div>
        <div className="flex items-baseline justify-between gap-3">
          <span className="text-[12px] leading-4 text-muted-foreground">
            {t('documents.remaining')}
          </span>
          <MonoAnnotation>
            {documentsRemaining === null ? '—' : documentsRemaining}
          </MonoAnnotation>
        </div>
      </div>
    </div>
  );
}
