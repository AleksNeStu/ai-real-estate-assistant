import { getTranslations } from 'next-intl/server';

import { WaitlistForm } from '@/components/landing/waitlist-form';
import { LANDING_SLOTS, withUtm } from '@/lib/utm';

/**
 * The three exits.
 *
 * The repository stays open, so the page offers three honest ways forward and
 * none of them is a dead end: run it yourself, move to the hosted tier, or
 * build something like it with the studio.
 */
export async function ExitCards() {
  const t = await getTranslations('landing');

  const code = [t('exits.run.code1'), t('exits.run.code2'), t('exits.run.code3'), t('exits.run.code4')];

  return (
    <section id="open" className="mx-auto max-w-[1248px] scroll-mt-16 px-6 pt-24">
      <div className="mb-8 flex max-w-[760px] flex-col gap-3">
        <h2 className="text-section font-semibold">{t('exits.title')}</h2>
        <p className="text-muted-foreground">{t('exits.body')}</p>
      </div>

      <div className="grid grid-cols-1 overflow-hidden rounded-[10px] border border-border lg:grid-cols-[1.15fr_1fr_1fr]">
        <div className="flex flex-col gap-3.5 bg-muted p-6">
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

          <div className="mt-auto flex items-center gap-2">
            <a
              href={withUtm('https://github.com/AleksNeStu/ai-real-estate-assistant/fork', {
                medium: 'landing',
                campaign: 'oss',
                content: LANDING_SLOTS.exitFork,
              })}
              target="_blank"
              rel="noreferrer"
              className="inline-flex h-10 items-center rounded-md bg-foreground px-4 text-[14px] font-medium text-background transition-colors hover:bg-foreground/90"
            >
              {t('exits.run.ctaFork')}
            </a>
            <a
              href={withUtm('https://github.com/AleksNeStu/ai-real-estate-assistant/issues', {
                medium: 'landing',
                campaign: 'oss',
                content: LANDING_SLOTS.exitIssue,
              })}
              target="_blank"
              rel="noreferrer"
              className="px-2 text-[14px] font-medium text-foreground hover:underline"
            >
              {t('exits.run.ctaSuggest')} →
            </a>
          </div>
        </div>

        <div className="flex flex-col gap-3.5 border-t border-border p-6 lg:border-l lg:border-t-0">
          <div className="flex items-baseline justify-between gap-3">
            <h3 className="text-h3 font-semibold">{t('exits.hosted.title')}</h3>
            <span className="font-mono text-[12px] font-medium text-warning">
              {t('exits.hosted.badge')}
            </span>
          </div>

          <p className="text-[14px] leading-[22px] text-muted-foreground">{t('exits.hosted.body')}</p>

          <table className="text-[13px]">
            <tbody>
              {[
                [t('exits.hosted.priceFree'), t('exits.hosted.priceFreeValue')],
                [t('exits.hosted.pricePro'), t('exits.hosted.priceProValue')],
                [t('exits.hosted.priceEnterprise'), t('exits.hosted.priceEnterpriseValue')],
              ].map(([label, value], index) => (
                <tr key={label} className={index === 2 ? 'border-y border-border' : 'border-t border-border'}>
                  <td className="py-[7px]">{label}</td>
                  <td className="py-[7px] text-right font-mono text-[13px] font-semibold">{value}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="mt-auto flex flex-col items-start gap-1.5">
            <WaitlistForm />
            <a
              href={withUtm('https://propvectorai.com/', {
                medium: 'landing',
                campaign: 'propvector',
                content: LANDING_SLOTS.exitHosted,
              })}
              target="_blank"
              rel="noreferrer"
              className="text-[13px] text-foreground hover:underline"
            >
              {t('exits.hosted.link')} ↗
            </a>
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
            <a
              href={withUtm('https://nestlab.tech/services', {
                medium: 'landing',
                campaign: 'studio',
                content: LANDING_SLOTS.exitStudio,
              })}
              target="_blank"
              rel="noreferrer"
              className="inline-flex h-10 items-center rounded-md bg-foreground px-4 text-[14px] font-medium text-background transition-colors hover:bg-foreground/90"
            >
              {t('exits.studio.ctaTalk')}
            </a>
            <a
              href={withUtm('https://github.com/AleksNeStu/ai-real-estate-assistant/discussions', {
                medium: 'landing',
                campaign: 'studio',
                content: LANDING_SLOTS.exitDiscussion,
              })}
              target="_blank"
              rel="noreferrer"
              className="text-[13px] text-foreground hover:underline"
            >
              {t('exits.studio.ctaDiscussion')} →
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}
