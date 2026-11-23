import Link from 'next/link';
import { getTranslations } from 'next-intl/server';

import { PlaceFiguresView } from '@/components/valuation/place-figures';
import { MonoAnnotation } from '@/components/ui/mono-annotation';
import { PageHeader } from '@/components/ui/page-header';
import type { PlaceFigures } from '@/lib/api/places';

/**
 * A place, as the register holds it.
 *
 * The page says four things about a city or a district: what a square metre
 * costs there, how many registered sales that is measured on, the period
 * those sales cover, and the sales themselves. Nothing else - a place that
 * carries more than the register can say is a page with a claim on it.
 *
 * The figures are read by the route, which has to read them anyway to decide
 * whether the page exists at all and to write the structured data onto it.
 * Passing them in keeps the page a rendering of one read.
 */
export interface PlacePageProps {
  locale: string;
  figures: PlaceFigures;
}

export default async function PlacePage({ locale, figures }: PlacePageProps) {
  const t = await getTranslations({ locale, namespace: 'pages.place' });

  const place = figures.district
    ? `${figures.district}, ${figures.place}`
    : figures.place;

  return (
    <div className="flex min-h-[calc(100vh-56px)] flex-col gap-6 px-6 py-6">
      <PageHeader
        title={t('heading', { place })}
        description={t('basis', {
          count: figures.sample_size,
          start: figures.period_start ?? '',
          end: figures.period_end ?? '',
        })}
        actions={<MonoAnnotation>{t('registerSource')}</MonoAnnotation>}
      />

      <PlaceFiguresView figures={figures} locale={locale} />

      <div className="flex flex-wrap gap-x-6 gap-y-1">
        {figures.district ? (
          <Link
            href={`/${locale}/valuation/${figures.slug}`}
            className="text-[14px] font-medium text-foreground hover:underline"
          >
            {t('wholeCity', { place: figures.place })}
          </Link>
        ) : null}
        <Link
          href={`/${locale}/valuation`}
          className="text-[14px] font-medium text-foreground hover:underline"
        >
          {t('backToForm')}
        </Link>
      </div>
    </div>
  );
}
