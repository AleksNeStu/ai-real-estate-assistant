import { getTranslations } from 'next-intl/server';

import { OutboundLink } from '@/components/shell/outbound-link';
import { LANDING_SLOTS, withUtm } from '@/lib/utm';

/**
 * The studio strip.
 *
 * Two entries: the hosted version of this project and the studio that
 * maintains it. The other products of the studio are not advertised here -
 * they are still in development, and this page must not promise them.
 */
export async function StudioStrip() {
  const t = await getTranslations('landing');

  const entries = [
    {
      name: t('studio.propvector.name'),
      body: t('studio.propvector.body'),
      url: 'https://propvectorai.com/',
      campaign: 'propvector' as const,
    },
    {
      name: t('studio.nestlab.name'),
      body: t('studio.nestlab.body'),
      url: 'https://nestlab.tech/',
      campaign: 'studio' as const,
    },
  ];

  return (
    <section className="mx-auto max-w-[1248px] px-6 pt-24">
      <div className="grid grid-cols-1 gap-14 lg:grid-cols-[360px_minmax(0,1fr)]">
        <h2 className="text-section font-semibold">{t('studio.title')}</h2>

        <div className="border-t border-foreground">
          {entries.map((entry) => (
            <OutboundLink
              key={entry.name}
              outboundTarget={entry.name}
              campaign={entry.campaign}
              slot={LANDING_SLOTS.studioStrip}
              href={withUtm(entry.url, {
                medium: 'landing',
                campaign: entry.campaign,
                content: LANDING_SLOTS.studioStrip,
              })}
              target="_blank"
              rel="noreferrer"
              className="grid grid-cols-1 items-baseline gap-6 border-b border-border py-[18px] transition-colors hover:bg-muted/50 sm:grid-cols-[230px_minmax(0,1fr)_150px]"
            >
              <span className="font-semibold">{entry.name}</span>
              <span className="text-[15px] text-muted-foreground">{entry.body}</span>
              <span className="text-right font-mono text-[13px]">
                {entry.name === t('studio.propvector.name')
                  ? t('studio.propvector.url')
                  : t('studio.nestlab.url')}{' '}
                ↗
              </span>
            </OutboundLink>
          ))}
        </div>
      </div>
    </section>
  );
}
