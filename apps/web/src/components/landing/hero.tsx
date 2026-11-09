import { getTranslations } from 'next-intl/server';
import { Search } from 'lucide-react';

import { HeroInstrument } from '@/components/landing/hero-instrument';
import { LANDING_SLOTS, withSlot, withUtm } from '@/lib/utm';

/**
 * The hero of the landing.
 *
 * Two columns: the promise and the instrument. The instrument is not a
 * picture of the product - it is the product, running the demo query against
 * the live catalogue.
 */
export async function Hero({ locale }: { locale: string }) {
  const t = await getTranslations('landing');

  const chips = [1, 2, 3, 4, 5, 6].map((index) => ({
    label: t(`chips.${index}`),
    href: withSlot(`/${locale}/search?q=${encodeURIComponent(t(`chips.${index}`))}`, LANDING_SLOTS.chips),
  }));

  const stats = [
    { value: t('hero.statLicence'), label: t('hero.statLicenceLabel') },
    { value: t('hero.statLanguages'), label: t('hero.statLanguagesLabel') },
    { value: t('hero.statProviders'), label: t('hero.statProvidersLabel') },
    { value: t('hero.statDeploy'), label: t('hero.statDeployLabel') },
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
              <a
                href={withSlot(`/${locale}/chat`, LANDING_SLOTS.heroAssistant)}
                className="text-foreground hover:underline"
              >
                {t('hero.ctaAssistant')} →
              </a>
              <a
                href={withUtm('https://github.com/AleksNeStu/ai-real-estate-assistant', {
                  medium: 'landing',
                  campaign: 'oss',
                  content: LANDING_SLOTS.heroStar,
                })}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 text-foreground hover:underline"
              >
                <GitHubMark className="h-4 w-4" aria-hidden="true" />
                {t('hero.ctaGithub')}
              </a>
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

/** The GitHub mark. Lucide dropped the brand icons, so the mark is inline. */
function GitHubMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 16 16" className={className} fill="currentColor" aria-hidden="true">
      <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27s1.36.09 2 .27c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8Z" />
    </svg>
  );
}
