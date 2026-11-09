import { getTranslations } from 'next-intl/server';

import { Link } from '@/i18n/navigation';

/**
 * The 404 page.
 *
 * The number is the headline and it is set in mono: it is data, and data is
 * set in the mono face. The page says what happened and offers the two ways
 * forward - back into the product, or back to the front page.
 *
 * This copy lives in the `[locale]` segment so it can use the catalogue; the
 * root `app/not-found.tsx` stays in English because it renders outside the
 * intl provider.
 */
export default async function NotFound() {
  const t = await getTranslations('designStates');

  return (
    <div className="mx-auto flex max-w-[1200px] flex-col items-start gap-5 px-6 py-24">
      <span className="font-mono text-[64px] font-medium leading-none tracking-[-0.04em] text-foreground">
        {t('notFound.code')}
      </span>
      <h1 className="m-0 text-[34px] font-semibold leading-10 tracking-[-0.03em]">
        {t('notFound.title')}
      </h1>
      <p className="m-0 max-w-[560px] text-[16px] leading-[25px] text-muted-foreground">
        {t('notFound.body')}
      </p>
      <div className="flex flex-wrap items-center gap-2">
        <Link
          href="/search"
          className="inline-flex h-10 items-center rounded-md bg-action px-[18px] text-[14px] font-medium text-action-foreground transition-colors hover:bg-action/90"
        >
          {t('notFound.ctaSearch')}
        </Link>
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
