'use client';

import Link from 'next/link';
import { useTranslations } from 'next-intl';

import { formatPrice } from '@/lib/format';
import type { PlaceFigures } from '@/lib/api/places';

/**
 * What the register says about a place.
 *
 * A place has no flat to price, so there is no estimate here: there is the
 * price a square metre costs there, the registered sales that figure is
 * measured on, the period those sales cover and the sales themselves. The
 * number is loud and everything that made it is quiet - how many sales it
 * rests on, the period they cover, the area they came from - so a reader who
 * wants to know whether to believe it can read all of it without leaving the
 * page.
 */
export interface PlaceFiguresProps {
  figures: PlaceFigures;
  locale: string;
  className?: string;
}

export function PlaceFiguresView({ figures, locale, className }: PlaceFiguresProps) {
  const t = useTranslations('pages.place');
  const currency = figures.currency || 'PLN';

  const facts = [
    {
      label: t('registered'),
      value:
        figures.registered_count != null
          ? t('registeredCount', { count: figures.registered_count })
          : '—',
    },
    {
      label: t('sample'),
      value: t('sampleCount', { count: figures.sample_size }),
    },
    {
      label: t('period'),
      value:
        figures.period_start && figures.period_end
          ? `${figures.period_start} → ${figures.period_end}`
          : '—',
    },
    { label: t('comparisonArea'), value: figures.comparison_area || '—' },
    { label: t('confidence'), value: figures.confidence || '—' },
  ];

  return (
    <div
      className={['flex flex-col gap-6', className].filter(Boolean).join(' ')}
      data-testid="place-figures"
    >
      <div className="grid grid-cols-1 gap-x-4 border-t border-foreground sm:grid-cols-2 lg:grid-cols-4">
        {figures.median_price_per_sqm != null ? (
          <div className="flex flex-col gap-0.5 border-b border-border py-3 pr-2">
            <span className="text-[12px] leading-4 text-muted-foreground">
              {t('medianPerSqm')}
            </span>
            <span className="font-mono text-h3 font-semibold leading-6 text-foreground">
              {formatPrice(figures.median_price_per_sqm, currency, locale)}/m²
            </span>
            {figures.first_quartile_price_per_sqm != null &&
            figures.third_quartile_price_per_sqm != null ? (
              <span className="font-mono text-[11px] leading-4 text-muted-foreground">
                {formatPrice(figures.first_quartile_price_per_sqm, currency, locale)} –{' '}
                {formatPrice(figures.third_quartile_price_per_sqm, currency, locale)}/m²
              </span>
            ) : null}
          </div>
        ) : null}

        {facts.map((fact) => (
          <div key={fact.label} className="flex flex-col gap-0.5 border-b border-border py-3 pr-2">
            <span className="text-[12px] leading-4 text-muted-foreground">{fact.label}</span>
            <span className="text-[14px] leading-6 text-foreground">{fact.value}</span>
          </div>
        ))}
      </div>

      {figures.notes.length ? (
        <ul className="flex flex-col gap-1">
          {figures.notes.map((note, index) => (
            <li key={`${note}-${index}`} className="text-[12px] leading-5 text-muted-foreground">
              {note}
            </li>
          ))}
        </ul>
      ) : null}

      {figures.comparables.length ? (
        <section className="flex flex-col gap-2">
          <h2 className="text-[14px] font-semibold text-foreground">{t('sales')}</h2>
          <ul className="border-t border-foreground">
            {figures.comparables.map((comparable, index) => (
              <li
                key={`${comparable.deed_reference ?? 'sale'}-${index}`}
                className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 border-b border-border py-2.5"
              >
                <span className="text-[14px] leading-5 text-foreground">
                  {comparable.address}
                </span>
                <span className="font-mono text-[12px] leading-5 text-muted-foreground">
                  {comparable.area_sqm.toFixed(1)} m² ·{' '}
                  {formatPrice(comparable.price, currency, locale)} (
                  {formatPrice(comparable.price_per_sqm, currency, locale)}/m²) ·{' '}
                  {comparable.transaction_date}
                  {comparable.deed_reference ? ` · ${comparable.deed_reference}` : ''}
                </span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {figures.districts.length ? (
        <nav className="flex flex-col gap-2" aria-label={t('districts')}>
          <h2 className="text-[14px] font-semibold text-foreground">{t('districts')}</h2>
          <ul className="flex flex-wrap gap-x-4 gap-y-1">
            {figures.districts.map((district) => (
              <li key={district.slug}>
                <Link
                  href={`/${locale}/valuation/${figures.slug}/${district.slug}`}
                  className="text-[14px] font-medium text-foreground hover:underline"
                >
                  {district.name}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      ) : null}
    </div>
  );
}
