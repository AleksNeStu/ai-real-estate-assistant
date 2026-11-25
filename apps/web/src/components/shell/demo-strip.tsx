'use client';

import { useTranslations } from 'next-intl';

import { OutboundLink } from '@/components/shell/outbound-link';
import { APP_SLOTS, withUtm } from '@/lib/utm';

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
      <OutboundLink
        outboundTarget="github.com"
        campaign="oss"
        slot={APP_SLOTS.chatBanner}
        href={withUtm(
          'https://github.com/AleksNeStu/ai-real-estate-assistant#quick-start',
          { medium: 'app', campaign: 'oss', content: APP_SLOTS.chatBanner }
        )}
        className="hidden shrink-0 text-foreground transition-colors hover:underline sm:inline"
      >
        {t('demoStrip.cta')}
      </OutboundLink>
    </div>
  );
}
