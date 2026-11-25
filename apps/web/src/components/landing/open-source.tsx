import { getTranslations } from 'next-intl/server';

import { OutboundLink } from '@/components/shell/outbound-link';
import { LANDING_SLOTS, withUtm } from '@/lib/utm';

/**
 * The open-source section.
 *
 * The material that speaks about the code rather than about the product: the
 * licence, the fork, the two commands that start it and the studio that
 * maintains it. It sits at the bottom of the landing on purpose - it is real
 * information a buyer deserves, but it is not what the first screen has to
 * answer.
 */
export async function OpenSource() {
  const t = await getTranslations('landing');

  const code = [t('exits.run.code1'), t('exits.run.code2'), t('exits.run.code3'), t('exits.run.code4')];

  return (
    <section id="open" className="mx-auto max-w-[1248px] scroll-mt-16 px-6 pt-24">
      <div className="mb-8 flex max-w-[760px] flex-col gap-3">
        <h2 className="text-section font-semibold">{t('opensource.title')}</h2>
        <p className="text-muted-foreground">{t('opensource.body')}</p>
      </div>

      <div className="grid grid-cols-1 overflow-hidden rounded-lg border border-border bg-muted lg:grid-cols-2">
        <div className="flex flex-col gap-3.5 p-6">
          <div className="flex items-baseline justify-between gap-3">
            <h3 className="text-h3 font-semibold">{t('exits.run.title')}</h3>
            <span className="font-mono text-[12px] font-medium text-success">
              {t('exits.run.badge')}
            </span>
          </div>

          <div className="rounded-md bg-foreground px-3.5 py-3 font-mono text-[12.5px] leading-5 text-background">
            {code.map((line) => (
              <div key={line} className="flex gap-2">
                {line.startsWith('$') ? <span className="text-background/60">$</span> : null}
                <span>{line.startsWith('$') ? line.slice(1).trim() : line}</span>
              </div>
            ))}
          </div>

          <p className="text-[14px] leading-[22px] text-muted-foreground">{t('exits.run.body')}</p>

          <div className="mt-auto flex flex-col items-start gap-2">
            <OutboundLink
              outboundTarget="github"
              campaign="oss"
              slot={LANDING_SLOTS.exitFork}
              href={withUtm('https://github.com/AleksNeStu/ai-real-estate-assistant/fork', {
                medium: 'landing',
                campaign: 'oss',
                content: LANDING_SLOTS.exitFork,
              })}
              target="_blank"
              rel="noreferrer"
              className="inline-flex h-10 items-center rounded-md bg-foreground px-4 text-[14px] font-medium text-background transition-colors hover:bg-foreground/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
            >
              {t('exits.run.ctaFork')}
            </OutboundLink>
            <OutboundLink
              outboundTarget="github"
              campaign="oss"
              slot={LANDING_SLOTS.exitIssue}
              href={withUtm('https://github.com/AleksNeStu/ai-real-estate-assistant/issues', {
                medium: 'landing',
                campaign: 'oss',
                content: LANDING_SLOTS.exitIssue,
              })}
              target="_blank"
              rel="noreferrer"
              className="text-[13px] font-medium text-foreground hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
            >
              {t('exits.run.ctaSuggest')} →
            </OutboundLink>
          </div>
        </div>

        <div className="flex flex-col gap-3.5 border-t border-border p-6 lg:border-l lg:border-t-0">
          <div className="flex items-baseline justify-between gap-3">
            <h3 className="text-h3 font-semibold">{t('exits.studio.title')}</h3>
            <span className="font-mono text-[12px] font-medium text-muted-foreground">
              {t('exits.studio.badge')}
            </span>
          </div>

          <p className="text-[14px] leading-[22px] text-muted-foreground">{t('exits.studio.body')}</p>
          <p className="text-[14px] leading-[22px]">{t('exits.studio.body2')}</p>

          <div className="mt-auto flex flex-col items-start gap-2">
            <OutboundLink
              outboundTarget="nestlab"
              campaign="studio"
              slot={LANDING_SLOTS.exitStudio}
              href={withUtm('https://nestlab.tech/services', {
                medium: 'landing',
                campaign: 'studio',
                content: LANDING_SLOTS.exitStudio,
              })}
              target="_blank"
              rel="noreferrer"
              className="inline-flex h-10 items-center rounded-md bg-foreground px-4 text-[14px] font-medium text-background transition-colors hover:bg-foreground/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
            >
              {t('exits.studio.ctaTalk')}
            </OutboundLink>
            <OutboundLink
              outboundTarget="github"
              campaign="studio"
              slot={LANDING_SLOTS.exitDiscussion}
              href={withUtm('https://github.com/AleksNeStu/ai-real-estate-assistant/discussions', {
                medium: 'landing',
                campaign: 'studio',
                content: LANDING_SLOTS.exitDiscussion,
              })}
              target="_blank"
              rel="noreferrer"
              className="text-[13px] font-medium text-foreground hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
            >
              {t('exits.studio.ctaDiscussion')} →
            </OutboundLink>
          </div>
        </div>
      </div>
    </section>
  );
}
