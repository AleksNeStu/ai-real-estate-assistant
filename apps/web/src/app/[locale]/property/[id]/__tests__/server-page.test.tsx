import * as serverApi from '@/lib/api/server';
import { buildPropertyStructuredData } from '@/lib/structured-data';
import type { Property } from '@/lib/types';

import { generateMetadata } from '../page';

/**
 * The server side of the listing page.
 *
 * The page is read on the server now, so the metadata and the structured
 * data are decided there - and they are what a crawler and an answer engine
 * read. The view is covered by the test beside this one.
 */

jest.mock('@/lib/api/server', () => ({
  fetchServerProperty: jest.fn(),
  fetchServerRelated: jest.fn(),
}));

const listing: Property = {
  id: 'listing-1',
  title: 'Bright two-room apartment',
  description: 'A sunny apartment close to the park.',
  city: 'Kraków',
  country: 'Poland',
  district: 'Stare Miasto',
  address: 'Brzozowa 12',
  latitude: 50.0614,
  longitude: 19.9374,
  property_type: 'apartment',
  listing_type: 'rent',
  rooms: 2,
  bathrooms: 1,
  area_sqm: 54,
  floor: 3,
  year_built: 2015,
  price: 2800,
  currency: 'PLN',
  has_parking: false,
  has_garden: false,
  has_pool: false,
  has_garage: false,
  has_bike_room: false,
};

describe('the metadata of a listing', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (serverApi.fetchServerProperty as jest.Mock).mockResolvedValue(listing);
  });

  it('names the listing and where it is', async () => {
    const metadata = await generateMetadata({
      params: Promise.resolve({ locale: 'en', id: 'listing-1' }),
    });

    expect(String(metadata.title)).toContain('Bright two-room apartment');
    expect(String(metadata.title)).toContain('Kraków');
    expect(String(metadata.description)).toContain('sunny apartment');
  });

  it('points the canonical at the listing itself', async () => {
    const metadata = await generateMetadata({
      params: Promise.resolve({ locale: 'en', id: 'listing-1' }),
    });

    const alternates = metadata.alternates as { canonical?: string; languages?: Record<string, string> };
    expect(alternates.canonical).toBe('https://realty.kittray.com/en/property/listing-1');
    // The cluster points at the SAME listing in every language, not at the
    // home pages.
    expect(alternates.languages?.pl).toBe('https://realty.kittray.com/pl/property/listing-1');
    expect(alternates.languages?.['x-default']).toBe(
      'https://realty.kittray.com/pl/property/listing-1',
    );
  });

  it('keeps a listing the catalogue does not hold out of the index', async () => {
    (serverApi.fetchServerProperty as jest.Mock).mockResolvedValue(null);

    const metadata = await generateMetadata({
      params: Promise.resolve({ locale: 'en', id: 'missing' }),
    });

    expect(metadata.robots).toMatchObject({ index: false, follow: true });
  });
});

describe('the structured data of a listing', () => {
  it('describes the listing, its position and its offer', () => {
    const document = buildPropertyStructuredData(listing, {
      url: 'https://realty.kittray.com/en/property/listing-1',
      locale: 'en',
    });

    const graph = document['@graph'] as Record<string, unknown>[];
    const property = graph.find((node) => node['@type'] === 'Property');
    expect(property).toBeDefined();

    const node = property as Record<string, any>;
    expect(node.name).toBe('Bright two-room apartment');
    expect(node.numberOfRooms).toBe(2);
    expect(node.geo).toMatchObject({ latitude: 50.0614, longitude: 19.9374 });
    expect(node.floorSize).toMatchObject({ value: 54 });
    expect(node.offers).toMatchObject({ price: 2800, priceCurrency: 'PLN' });

    // The breadcrumb says where the listing sits.
    const breadcrumb = graph.find((node) => node['@type'] === 'BreadcrumbList');
    expect(breadcrumb).toBeDefined();
  });

  it('carries no offer for a listing without a price', () => {
    const document = buildPropertyStructuredData(
      { ...listing, price: undefined },
      { url: 'https://realty.kittray.com/en/property/listing-1', locale: 'en' },
    );

    const graph = document['@graph'] as Record<string, unknown>[];
    const property = graph.find((node) => node['@type'] === 'Property') as Record<string, any>;
    expect(property.offers).toBeUndefined();
  });
});
