import type { Metadata } from 'next';

import { fetchServerProperty, fetchServerRelated } from '@/lib/api/server';
import { languageAlternates } from '@/lib/metadata';
import { buildPropertyStructuredData } from '@/lib/structured-data';
import { absoluteUrl } from '@/lib/site';

import PropertyView from './property-view';

interface PropertyPageProps {
  params: Promise<{ locale: string; id: string }>;
}

/**
 * The page of one listing.
 *
 * WHY THE PAGE IS A SERVER COMPONENT
 *
 * The listing page was a client component: it fetched the listing after the
 * page had loaded. A crawler that does not run the JavaScript - and every
 * answer engine that quotes a page - received an empty shell with the site's
 * own title and no idea what the page was about. The page also had no
 * canonical, no structured data and no entry in the sitemap, so the one page
 * of the site that a buyer actually searches for ("two-room apartment in
 * Kraków, Old Town") was the one page a search engine could not read.
 *
 * The listing is now read on the server and handed to the client view, which
 * keeps everything the reader sees - the heart, the mortgage estimate, the
 * comparables - exactly as it was. What is new is that the page now arrives
 * with its content, its title and its structured data.
 */

/**
 * The title and the description of one listing.
 *
 * They are built from the listing itself - its name, its city, its price,
 * its rooms - because that is what a searcher types. The catalogue's titles
 * are sentences ("two-room apartment in Old Town"), which read as a title
 * and as a query at the same time.
 */
function describe(property: {
  title?: string;
  city: string;
  property_type?: string;
  district?: string;
  rooms?: number;
  area_sqm?: number;
  price?: number;
  currency?: string;
  description?: string;
}): { title: string; description: string } {
  const name = property.title || `${property.property_type ?? 'property'} in ${property.city}`;
  const where = [property.district, property.city].filter(Boolean).join(', ');
  const facts = [
    property.rooms ? `${property.rooms} room${property.rooms === 1 ? '' : 's'}` : null,
    property.area_sqm ? `${property.area_sqm} m²` : null,
    property.price
      ? `${property.price.toLocaleString('en-US')} ${property.currency ?? 'PLN'}`
      : null,
  ].filter(Boolean);

  const title = `${name} — ${where}`;
  const description =
    property.description?.trim() ||
    `${name} in ${where}${facts.length ? `. ${facts.join(', ')}` : ''}. Search, compare and analyse listings with AI Real Estate Assistant.`;

  return { title, description: description.slice(0, 300) };
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string; id: string }>;
}): Promise<Metadata> {
  const { locale, id } = await params;
  const property = await fetchServerProperty(id);
  const url = absoluteUrl(`/${locale}/property/${id}`);

  if (!property) {
    // A listing that is not there is not a page anybody should index.
    return {
      title: 'Property not found',
      robots: { index: false, follow: true },
      alternates: { canonical: url, languages: languageAlternates(`/property/${id}`) },
    };
  }

  const { title, description } = describe(property);

  return {
    title,
    description,
    alternates: {
      canonical: url,
      // The same listing, in every language the site carries.
      languages: languageAlternates(`/property/${id}`),
    },
    openGraph: {
      title,
      description,
      url,
      type: 'website',
      images: property.images?.[0] ? [{ url: property.images[0] }] : undefined,
    },
    twitter: {
      card: 'summary_large_image',
      title,
      description,
    },
  };
}

export default async function PropertyPage({ params }: PropertyPageProps) {
  const { locale, id } = await params;

  const [property, related] = await Promise.all([
    fetchServerProperty(id),
    fetchServerRelated(id, 3),
  ]);

  const url = absoluteUrl(`/${locale}/property/${id}`);

  return (
    <>
      {property ? (
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify(
              buildPropertyStructuredData(property, { url, locale }),
            ),
          }}
        />
      ) : null}
      <PropertyView
        propertyId={id}
        initialProperty={property}
        initialRelated={related}
      />
    </>
  );
}
