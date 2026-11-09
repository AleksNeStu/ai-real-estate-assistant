'use client';

import { useTranslations } from 'next-intl';

/**
 * The strip under the top bar of the application.
 *
 * It states what the visitor is looking at: a demo that answers with a model
 * the studio pays for, so exploring costs nothing and no key is needed. The
 * link goes to the quick start, because the other way to run this is with
 * your own key.
 *
 * The strip is honest by construction - it names the model rather than
 * claiming a local one, because the deployment answers with a hosted model
 * unless it is configured otherwise.
 */
export function DemoStrip() {
  const t = useTranslations('shell');

  if (process.env.NEXT_PUBLIC_DEMO_MODE !== 'true') {
    return null;
  }

  return (
    <div
      role="status"
      className="flex h-9 items-center justify-center gap-2.5 border-b border-border bg-muted px-6 text-[13px] text-muted-foreground"
    >
      <span className="size-1.5 shrink-0 rounded-full bg-success" aria-hidden="true" />
      <span className="truncate">
        <span className="font-medium text-foreground">{t('demoPill')}.</span>{' '}
        {t('demoStrip.note')}
      </span>
      <a
        href="https://github.com/AleksNeStu/ai-real-estate-assistant#quick-start?utm_source=realty.kittray.com&utm_medium=app&utm_campaign=oss&utm_content=chat_banner"
        className="hidden shrink-0 text-foreground transition-colors hover:underline sm:inline"
      >
        {t('demoStrip.cta')}
      </a>
    </div>
  );
}
