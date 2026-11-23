import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { getTranslations } from 'next-intl/server';

import PlacePage from '@/components/valuation/place-page';
import { RegisterValuation } from '@/components/valuation/register-valuation';
import { ValuationShare } from '@/components/valuation/valuation-share';
import { MonoAnnotation } from '@/components/ui/mono-annotation';
import { PageHeader } from '@/components/ui/page-header';
import { fetchServerPlaceFigures, fetchServerValuation } from '@/lib/api/server';
import { languageAlternates, OG_IMAGE } from '@/lib/metadata';
import { absoluteUrl } from '@/lib/site';
import { buildValuationStructuredData, buildPlaceStructuredData } from '@/lib/structured-data';
import { decodeValuationSlug, type ValuationSubject } from '@/lib/valuation-slug';

interface ValuationRouteProps {
  params: Promise<{ locale: string; place: string }>;
}

/**
 * Two kinds of page, one path.
 *
 * `/valuation/{slug}` is the answer about one address - the slug carries the
 * city, the street, the area and the rooms. `/valuation/{city}` is the
 * figures of a whole city, and `/valuation/{city}/{district}` the figures of
 * one district of it.
 *
 * The address slug is the one with a separator in it; a city slug is a single
 * word. So the route reads the segment and hands it to the page it names.
 *
 * WHY THE ANSWER IS READ ON THE SERVER
 *
 * The interactive valuation page answers in the browser: the reader types an
 * address, the register answers, and the answer is gone with the tab. It
 * cannot be shared, it cannot be indexed, and it carries no structured data.
 *
 * This page is the answer with a URL. The address is in the link, so the
 * page is reached by the same address every time - and because the page is
 * read on the server, a crawler that does not run the JavaScript receives
 * the estimate, the sales it rests on, the period they cover and the
 * structured data, not an empty shell.
 */
const isAddressSlug = (place: string): boolean => place.includes('~');

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string; place: string }>;
}): Promise<Metadata> {
  const { locale, place } = await params;
  return isAddressSlug(place) ? addressMetadata(locale, place) : placeMetadata(locale, place);
}

async function addressMetadata(locale: string, slug: string): Promise<Metadata> {
  const subject = decodeValuationSlug(slug);
  const url = absoluteUrl(`/${locale}/valuation/${slug}`);
  const t = await getTranslations({ locale, namespace: 'pages.valuation' });

  if (!subject) {
    // A link that names no place is not a page anybody should index.
    return {
      title: t('page.notFoundTitle'),
      robots: { index: false, follow: true },
      alternates: { canonical: url, languages: languageAlternates(`/valuation/${slug}`) },
    };
  }

  const valuation = await fetchServerValuation(subject);
  const address = subject.street ? `${subject.street}, ${subject.city}` : subject.city;

  if (!valuation || typeof valuation.estimated_value !== 'number') {
    // Too few registered sales to price the place: the page carries the sales
    // but no number, and a page without an answer has nothing to index.
    return {
      title: t('page.title', { address }),
      description: t('page.noAnswerBody'),
      robots: { index: false, follow: true },
      alternates: { canonical: url, languages: languageAlternates(`/valuation/${slug}`) },
    };
  }

  const title = t('page.title', { address });
  const description = t('page.description', {
    count: valuation.sample_size ?? 0,
    start: valuation.period_start ?? '',
    end: valuation.period_end ?? '',
  });

  return {
    title,
    description,
    alternates: {
      canonical: url,
      // The same answer, in every language the site carries.
      languages: languageAlternates(`/valuation/${slug}`),
    },
    openGraph: {
      title,
      description,
      url,
      type: 'website',
      // A page-level social block REPLACES the one the layout declares, so it
      // has to carry the image too - otherwise a link preview of this page has
      // no picture.
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

async function placeMetadata(locale: string, slug: string): Promise<Metadata> {
  const url = absoluteUrl(`/${locale}/valuation/${slug}`);
  const t = await getTranslations({ locale, namespace: 'pages.place' });

  const figures = await fetchServerPlaceFigures(slug);
  if (!figures) {
    // The register holds nothing for this place: there is no page to index.
    return {
      title: t('page.notFoundTitle'),
      robots: { index: false, follow: true },
      alternates: { canonical: url, languages: languageAlternates(`/valuation/${slug}`) },
    };
  }

  const place = figures.district ? `${figures.district}, ${figures.place}` : figures.place;
  const title = t('page.title', { place });
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
      languages: languageAlternates(`/valuation/${slug}`),
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

/** The name the page shows: the register's own spelling of the place. */
function addressOf(subject: ValuationSubject, comparisonArea?: string | null): string {
  if (comparisonArea) return comparisonArea;
  return subject.street ? `${subject.street}, ${subject.city}` : subject.city;
}

export default async function ValuationRoute({ params }: ValuationRouteProps) {
  const { locale, place } = await params;

  if (!isAddressSlug(place)) {
    // A city: the figures the register holds for it.
    const figures = await fetchServerPlaceFigures(place);
    if (!figures) notFound();

    const url = absoluteUrl(`/${locale}/valuation/${place}`);
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
            __html: JSON.stringify(
              buildPlaceStructuredData(figures, { url, locale, basis }),
            ),
          }}
        />
        <PlacePage locale={locale} figures={figures} />
      </>
    );
  }

  const subject = decodeValuationSlug(place);
  if (!subject) notFound();

  const t = await getTranslations({ locale, namespace: 'pages.valuation' });
  const valuation = await fetchServerValuation(subject);
  const url = absoluteUrl(`/${locale}/valuation/${place}`);
  const address = addressOf(subject, valuation?.comparison_area);

  const basis =
    valuation && valuation.sample_size != null
      ? t('page.basis', {
          count: valuation.sample_size,
          start: valuation.period_start ?? '',
          end: valuation.period_end ?? '',
        })
      : undefined;

  return (
    <div className="flex min-h-[calc(100vh-56px)] flex-col gap-6 px-6 py-6">
      {valuation ? (
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify(
              buildValuationStructuredData(valuation, subject, { url, locale, basis }),
            ),
          }}
        />
      ) : null}

      <PageHeader
        title={t('page.heading', { address })}
        description={basis ?? t('page.noAnswerBody')}
        actions={<MonoAnnotation>{t('registerSource')}</MonoAnnotation>}
      />

      {valuation ? (
        <RegisterValuation result={valuation} />
      ) : (
        <p className="text-[14px] leading-5 text-muted-foreground">{t('page.noAnswerBody')}</p>
      )}

      <ValuationShare url={url} />

      <Link
        href={`/${locale}/valuation`}
        className="text-[14px] font-medium text-foreground hover:underline"
      >
        {t('page.backToForm')}
      </Link>
    </div>
  );
}
