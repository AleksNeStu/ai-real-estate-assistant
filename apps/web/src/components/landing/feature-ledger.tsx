import { getTranslations } from 'next-intl/server';

import { LANDING_SLOTS, withSlot } from '@/lib/utm';

/**
 * The features ledger.
 *
 * Six lines, each one a link into the part of the demo it describes. A ledger
 * and not a grid of cards: these are lines of an argument, not objects.
 */
export async function FeatureLedger({ locale }: { locale: string }) {
  const t = await getTranslations('landing');
  const features = [1, 2, 3, 4, 5, 6].map((index) => ({
    title: t(`features.${index}.title`),
    text: t(`features.${index}.text`),
    route: t(`features.${index}.route`),
  }));

  return (
    <section id="features" className="mx-auto max-w-[1248px] scroll-mt-16 px-6 pt-24">
      <div className="grid grid-cols-1 gap-14 lg:grid-cols-[360px_minmax(0,1fr)]">
        <div className="flex flex-col gap-3">
          <h2 className="text-section font-semibold">{t('features.title')}</h2>
          <p className="text-muted-foreground">{t('features.body')}</p>
        </div>

        <div className="border-t border-foreground">
          {features.map((feature) => (
            <a
              key={feature.title}
              href={withSlot(`/${locale}${feature.route}`, LANDING_SLOTS.features)}
              className="grid grid-cols-1 items-baseline gap-6 border-b border-border py-[18px] transition-colors hover:bg-muted/50 sm:grid-cols-[230px_minmax(0,1fr)_130px]"
            >
              <span className="font-semibold">{feature.title}</span>
              <span className="text-[15px] leading-[23px] text-muted-foreground">{feature.text}</span>
              <span className="text-right font-mono text-[13px] text-foreground">
                {feature.route} →
              </span>
            </a>
          ))}
        </div>
      </div>
    </section>
  );
}
