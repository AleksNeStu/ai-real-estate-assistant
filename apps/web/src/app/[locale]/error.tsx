'use client';

import { useTranslations } from 'next-intl';

import { Link } from '@/i18n/navigation';

/**
 * Next.js App Router error boundary.
 *
 * It catches a runtime error in any page and shows a fallback. The copy is
 * the design's: the title says what is true - the chat is unavailable, the
 * rest of the demo still works - and the digest is printed in mono, because
 * the digest is data and the operator needs it to find the failure in the
 * logs.
 *
 * This copy lives in the `[locale]` segment so it can use the catalogue; the
 * root `app/error.tsx` stays in English because it renders outside the
 * intl provider, when even the provider itself may be the thing that broke.
 */
export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const t = useTranslations('designStates');

  return (
    <div className="mx-auto flex max-w-[1200px] flex-col items-start gap-5 px-6 py-24">
      <h1 className="m-0 text-[34px] font-semibold leading-10 tracking-[-0.03em]">
        {t('error.title')}
      </h1>
      <p className="m-0 max-w-[560px] text-[16px] leading-[25px] text-muted-foreground">
        {t('error.body')}
      </p>
      {error.digest && (
        <p className="m-0 font-mono text-[12px] leading-4 text-muted-foreground">
          {t('error.id', { id: error.digest })}
        </p>
      )}
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={reset}
          className="inline-flex h-10 items-center rounded-md bg-action px-[18px] text-[14px] font-medium text-action-foreground transition-colors hover:bg-action/90"
        >
          {t('error.retry')}
        </button>
        <Link
          href="/"
          className="inline-flex h-10 items-center rounded-md border border-border px-4 text-[14px] font-medium text-foreground transition-colors hover:bg-muted"
        >
          {t('notFound.ctaHome')}
        </Link>
      </div>
    </div>
  );
}
