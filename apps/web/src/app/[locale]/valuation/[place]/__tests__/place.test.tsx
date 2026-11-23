import { render, screen } from '@testing-library/react';

import * as serverApi from '@/lib/api/server';
import type { PlaceFigures } from '@/lib/api/places';

import PlacePage from '@/components/valuation/place-page';
import { generateMetadata } from '../page';

/**
 * The pages of a place.
 *
 * A city or a district has no flat to price, so the page is not an estimate:
 * it is what the official register holds for that place - the price a square
 * metre costs there, how many registered sales the figure is measured on, the
 * period those sales cover and the sales themselves.
 *
 * The response below is a recorded reading of the register, and the test says
 * what a reader has to find on the page: the figures, their sample and their
 * period. A page that shows a number without saying where it came from is
 * not an answer.
 */
jest.mock('@/lib/api/server', () => ({
  fetchServerValuation: jest.fn(),
  fetchServerPlaceFigures: jest.fn(),
}));

// The metadata helper and the page read the catalogue through next-intl,
// whose server build is ESM and cannot be loaded by the test runtime. The
// catalogue itself is the real one, so the copy the test reads is the copy a
// reader reads.
jest.mock('next-intl/server', () => {
  const { formatMessage } = jest.requireActual('../../../../../../__mocks__/next-intl');
  const catalog = jest.requireActual('../../../../../../messages/en.json');

  const resolve = (namespace: string | undefined, key: string): unknown => {
    let scope: unknown = catalog;
    for (const part of [...(namespace ?? '').split('.'), ...key.split('.')]) {
      if (!part) continue;
      scope = (scope as Record<string, unknown> | undefined)?.[part];
    }
    return scope;
  };

  return {
    getTranslations: jest.fn(
      async ({ namespace }: { namespace?: string } = {}) =>
        (key: string, values?: Record<string, unknown>) => {
          const value = resolve(namespace, key);
          if (typeof value !== 'string') return key;
          return formatMessage(value, values);
        },
    ),
  };
});

const krakow: PlaceFigures = {
  place: 'Kraków',
  slug: 'krakow',
  district: '',
  district_slug: '',
  median_price_per_sqm: 15018.91,
  first_quartile_price_per_sqm: 11250.4,
  third_quartile_price_per_sqm: 19837.6,
  currency: 'PLN',
  source: 'rcn',
  confidence: 'high',
  sample_size: 1627,
  registered_count: 267603,
  comparison_area: 'Kraków',
  period_start: '2024-11-23',
  period_end: '2026-11-20',
  notes: [
    'Secondary market only (rynekWtorny).',
    'The register holds 267603 registered sale(s) between 2024-11-23 and 2026-11-20 for this place.',
  ],
  comparables: [
    {
      address: 'Floriańska 12',
      area_sqm: 48.5,
      price: 735000,
      price_per_sqm: 15155,
      transaction_date: '2026-10-30',
      rooms: 2,
      floor: null,
      deed_reference: '1234/2026',
    },
  ],
  districts: [
    { name: 'Old Town', slug: 'old-town' },
    { name: 'Podgórze', slug: 'podgorze' },
  ],
};

describe('the page of a place', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (serverApi.fetchServerPlaceFigures as jest.Mock).mockResolvedValue(krakow);
  });

  it('shows what a square metre costs there', async () => {
    render(await PlacePage({ locale: 'en', figures: krakow }));

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Kraków');
    expect(screen.getByTestId('place-figures')).toHaveTextContent('15,019');
  });

  it('says how many sales the register holds and how many it measured on', async () => {
    render(await PlacePage({ locale: 'en', figures: krakow }));

    const figures = screen.getByTestId('place-figures');
    expect(figures).toHaveTextContent('267,603 registered sales');
    expect(figures).toHaveTextContent('1,627 registered sales');
  });

  it('names the period the sales cover', async () => {
    render(await PlacePage({ locale: 'en', figures: krakow }));

    expect(screen.getByTestId('place-figures')).toHaveTextContent(
      '2024-11-23 → 2026-11-20',
    );
  });

  it('lists the sales the figure is measured on', async () => {
    render(await PlacePage({ locale: 'en', figures: krakow }));

    const figures = screen.getByTestId('place-figures');
    expect(figures).toHaveTextContent('Floriańska 12');
    expect(figures).toHaveTextContent('735,000');
  });

  it('links the districts of the city', async () => {
    render(await PlacePage({ locale: 'en', figures: krakow }));

    expect(screen.getByRole('link', { name: 'Old Town' })).toHaveAttribute(
      'href',
      '/en/valuation/krakow/old-town',
    );
  });
});

describe('the metadata of a place', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (serverApi.fetchServerPlaceFigures as jest.Mock).mockResolvedValue(krakow);
  });

  it('names the place and points the canonical at it', async () => {
    const metadata = await generateMetadata({
      params: Promise.resolve({ locale: 'en', place: 'krakow' }),
    });

    expect(String(metadata.title)).toContain('Kraków');
    const alternates = metadata.alternates as { canonical?: string };
    expect(alternates.canonical).toBe('https://realty.kittray.com/en/valuation/krakow');
  });

  it('keeps a place the register holds nothing for out of the index', async () => {
    (serverApi.fetchServerPlaceFigures as jest.Mock).mockResolvedValue(null);

    const metadata = await generateMetadata({
      params: Promise.resolve({ locale: 'en', place: 'wroclaw' }),
    });

    expect(metadata.robots).toMatchObject({ index: false, follow: true });
  });
});
