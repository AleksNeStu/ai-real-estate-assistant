import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { getTranslations } from 'next-intl/server';

import PlacePage from '@/components/valuation/place-page';
import { fetchServerPlaceFigures } from '@/lib/api/server';
import { languageAlternates, OG_IMAGE } from '@/lib/metadata';
import { absoluteUrl } from '@/lib/site';
import { buildPlaceStructuredData } from '@/lib/structured-data';

interface DistrictRouteProps {
  params: Promise<{ locale: string; place: string; district: string }>;
}

/**
 * One district of a city, as the register holds it.
 *
 * The register knows streets, not districts: the figures of a district are
 * the figures of the sales registered on the streets that district stands
 * on. The page says so, and it says how many sales the figure is measured
 * on and the period they cover.
 */
export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string; place: string; district: string }>;
}): Promise<Metadata> {
  const { locale, place, district } = await params;
  const path = `/valuation/${place}/${district}`;
  const url = absoluteUrl(`/${locale}${path}`);
  const t = await getTranslations({ locale, namespace: 'pages.place' });

  const figures = await fetchServerPlaceFigures(place, district);
  if (!figures) {
    // The register holds nothing for this district: there is no page to index.
    return {
      title: t('page.notFoundTitle'),
      robots: { index: false, follow: true },
      alternates: { canonical: url, languages: languageAlternates(path) },
    };
  }

  const name = figures.district ? `${figures.district}, ${figures.place}` : figures.place;
  const title = t('page.title', { place: name });
  const description = t('page.description', {
    count: figures.sample_size,
    start: figures.period_start ?? '',
    end: figures.period_end ?? '',
  });

  return {
    title,
    description,
    alternates: {
      canonical: url,
      languages: languageAlternates(path),
    },
    openGraph: {
      title,
      description,
      url,
      type: 'website',
      images: [OG_IMAGE],
    },
    twitter: {
      card: 'summary_large_image',
      title,
      description,
      images: [OG_IMAGE.url],
    },
  };
}

export default async function DistrictRoute({ params }: DistrictRouteProps) {
  const { locale, place, district } = await params;

  const figures = await fetchServerPlaceFigures(place, district);
  if (!figures) notFound();

  const url = absoluteUrl(`/${locale}/valuation/${place}/${district}`);
  const t = await getTranslations({ locale, namespace: 'pages.place' });
  const basis = t('basis', {
    count: figures.sample_size,
    start: figures.period_start ?? '',
    end: figures.period_end ?? '',
  });

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify(buildPlaceStructuredData(figures, { url, locale, basis })),
        }}
      />
      <PlacePage locale={locale} figures={figures} />
    </>
  );
}
