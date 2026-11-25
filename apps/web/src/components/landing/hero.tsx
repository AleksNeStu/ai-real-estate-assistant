import { getTranslations } from 'next-intl/server';
import { Search } from 'lucide-react';

import { HeroInstrument } from '@/components/landing/hero-instrument';
import { OutboundLink } from '@/components/shell/outbound-link';
import { LANDING_SLOTS, withSlot, withUtm } from '@/lib/utm';

/**
 * The hero of the landing.
 *
 * Two columns: the promise and the instrument. The instrument is not a
 * picture of the product - it is the product, running the demo query against
 * the live catalogue.
 *
 * The first screen answers three questions and no more: what this is, how to
 * try it now, and where the paid version is. The open-source material (the
 * licence, the fork, the commands) belongs further down the page, where the
 * open-source section carries it.
 */
export async function Hero({ locale }: { locale: string }) {
  const t = await getTranslations('landing');

  const chips = [1, 2, 3, 4, 5, 6].map((index) => ({
    label: t(`chips.${index}`),
    href: withSlot(`/${locale}/search?q=${encodeURIComponent(t(`chips.${index}`))}`, LANDING_SLOTS.chips),
  }));

  const stats = [
    { value: t('hero.statLanguages'), label: t('hero.statLanguagesLabel') },
    { value: t('hero.statProviders'), label: t('hero.statProvidersLabel') },
    { value: t('hero.statLive'), label: t('hero.statLiveLabel') },
    { value: t('hero.statNoKeys'), label: t('hero.statNoKeysLabel') },
  ];

  return (
    <>
      <section className="border-b border-border">
        <div className="mx-auto grid max-w-[1248px] grid-cols-1 items-stretch gap-14 px-6 pb-16 pt-[72px] lg:grid-cols-[minmax(0,1fr)_600px]">
          <div className="flex flex-col gap-6 pt-3">
            <h1 className="text-hero font-semibold">{t('hero.title')}</h1>
            <p className="max-w-[700px] text-lede text-muted-foreground">{t('hero.body')}</p>

            <form
              action={`/${locale}/search`}
              method="get"
              className="flex gap-1.5 rounded-[10px] border border-border bg-background p-1.5"
            >
              <label className="flex flex-1 items-center gap-2.5 px-2.5">
                <Search className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                <span className="sr-only">{t('hero.placeholder')}</span>
                <input
                  name="q"
                  type="search"
                  defaultValue={t('chips.1')}
                  placeholder={t('hero.placeholder')}
                  className="w-full border-0 bg-transparent text-[15px] text-foreground outline-none placeholder:text-muted-foreground"
                />
              </label>
              <button
                type="submit"
                className="inline-flex h-11 items-center gap-2 rounded-[7px] bg-action px-[18px] text-[15px] font-medium text-action-foreground transition-colors hover:bg-action/90"
              >
                {t('hero.ctaSearch')} →
              </button>
            </form>

            <div className="flex items-center gap-[18px] text-[14px] font-medium">
              <a href="#hosted" className="text-foreground hover:underline">
                {t('hero.ctaHosted')} →
              </a>
              <OutboundLink
                outboundTarget="nestlab"
                campaign="studio"
                slot={LANDING_SLOTS.heroTalk}
                href={withUtm('https://nestlab.tech/services', {
                  medium: 'landing',
                  campaign: 'studio',
                  content: LANDING_SLOTS.heroTalk,
                })}
                target="_blank"
                rel="noreferrer"
                className="text-foreground hover:underline"
              >
                {t('hero.ctaTalk')} →
              </OutboundLink>
            </div>

            <div className="mt-auto grid grid-cols-4 gap-7 border-t border-border pt-5">
              {stats.map((stat) => (
                <div key={stat.label} className="flex flex-col">
                  <span className="font-mono text-[20px] font-semibold">{stat.value}</span>
                  <span className="text-[12px] text-muted-foreground">{stat.label}</span>
                </div>
              ))}
            </div>
          </div>

          <HeroInstrument query={t('chips.1')} locale={locale} />
        </div>

        <div className="mx-auto flex max-w-[1248px] flex-wrap items-center gap-2 px-6 pb-10">
          <span className="mr-1 text-[13px] text-muted-foreground">{t('chips.label')}</span>
          {chips.map((chip) => (
            <a
              key={chip.label}
              href={chip.href}
              className="rounded-full border border-border px-3 py-[5px] text-[13px] leading-[18px] text-foreground transition-colors hover:bg-muted"
            >
              {chip.label}
            </a>
          ))}
        </div>
      </section>
    </>
  );
}
