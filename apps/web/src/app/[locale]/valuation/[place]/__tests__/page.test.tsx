import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

import * as serverApi from '@/lib/api/server';
import type { ValuationResponse } from '@/lib/api/tools';

import { generateMetadata, default as ValuationRoute } from '../page';

/**
 * The shareable valuation page.
 *
 * The page is read on the server, so the metadata and the structured data
 * are decided there - and they are what a crawler and an answer engine read.
 */
jest.mock('@/lib/api/server', () => ({
  fetchServerValuation: jest.fn(),
  fetchServerPlaceFigures: jest.fn(),
}));

// The metadata helper reads the message catalogue through next-intl, whose
// server build is ESM and cannot be loaded by the test runtime.
jest.mock('next-intl/server', () => ({
  getTranslations: jest.fn(async () => (key: string, values?: Record<string, unknown>) => {
    if (key === 'page.heading' || key === 'page.title') {
      return `Valuation of ${values?.address}`;
    }
    if (key === 'page.description' || key === 'page.basis') {
      return `${values?.count} registered sales`;
    }
    if (key === 'page.noAnswerBody') return 'Too few registered sales to price it.';
    if (key === 'page.notFoundTitle') return 'Valuation not found';
    if (key === 'page.backToForm') return 'Value another address';
    if (key === 'link.title') return 'A link to this answer';
    if (key === 'link.hint') return 'The same address always produces the same link.';
    if (key === 'registerSource') return 'RCN';
    return key;
  }),
}));

// The share button reaches the attribution module, which reads the visitor
// id from the browser - not what this test is about.
jest.mock('@/components/valuation/valuation-share', () => ({
  ValuationShare: ({ url }: { url: string }) => (
    <div data-testid="valuation-share">{url}</div>
  ),
}));

const valuation: ValuationResponse = {
  estimated_value: 959182,
  currency: 'PLN',
  source: 'rcn',
  confidence: 'high',
  sample_size: 26,
  comparison_area: 'Myśliwska, Kraków',
  period_start: '2025-05-12',
  period_end: '2026-10-12',
  price_per_sqm_median: 15986,
  low: 846539,
  high: 1082016,
  notes: ['Secondary market only (rynekWtorny).'],
  comparables: [
    {
      address: 'Myśliwska 68C',
      area_sqm: 60.49,
      price: 1200000,
      price_per_sqm: 19838,
      transaction_date: '2026-10-12',
      rooms: 3,
      floor: null,
      deed_reference: '1234/2026',
    },
  ],
};

describe('the metadata of a valuation', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (serverApi.fetchServerValuation as jest.Mock).mockResolvedValue(valuation);
  });

  it('names the place the link names', async () => {
    const metadata = await generateMetadata({
      params: Promise.resolve({ locale: 'en', place: 'krakow~mysliwska~60~3' }),
    });

    expect(String(metadata.title)).toContain('Valuation of');
  });

  it('points the canonical at the answer itself', async () => {
    const metadata = await generateMetadata({
      params: Promise.resolve({ locale: 'en', place: 'krakow~mysliwska~60~3' }),
    });

    const alternates = metadata.alternates as {
      canonical?: string;
      languages?: Record<string, string>;
    };
    expect(alternates.canonical).toBe(
      'https://realty.kittray.com/en/valuation/krakow~mysliwska~60~3',
    );
    // The cluster points at the SAME answer in every language.
    expect(alternates.languages?.pl).toBe(
      'https://realty.kittray.com/pl/valuation/krakow~mysliwska~60~3',
    );
    expect(alternates.languages?.['x-default']).toBe(
      'https://realty.kittray.com/en/valuation/krakow~mysliwska~60~3',
    );
  });

  it('keeps an answer the register cannot price out of the index', async () => {
    (serverApi.fetchServerValuation as jest.Mock).mockResolvedValue(null);

    const metadata = await generateMetadata({
      params: Promise.resolve({ locale: 'en', place: 'krakow~mysliwska~60~3' }),
    });

    expect(metadata.robots).toMatchObject({ index: false, follow: true });
  });

  it('keeps a link that names no place out of the index', async () => {
    const metadata = await generateMetadata({
      params: Promise.resolve({ locale: 'en', place: 'not-a-slug' }),
    });

    expect(metadata.robots).toMatchObject({ index: false, follow: true });
  });
});

describe('the page of a valuation', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (serverApi.fetchServerValuation as jest.Mock).mockResolvedValue(valuation);
  });

  it('carries the answer the crawler reads', async () => {
    const rendered = await ValuationRoute({
      params: Promise.resolve({ locale: 'en', place: 'krakow~mysliwska~60~3' }),
    });

    const html = renderToStaticMarkup(rendered);

    // The sales behind the estimate are on the page, not behind a click.
    expect(html).toContain('Myśliwska 68C');
    expect(html).toContain('1,200,000');
    // And the link to it.
    expect(html).toContain('https://realty.kittray.com/en/valuation/krakow~mysliwska~60~3');
  });

  it('carries the structured data the crawler reads', async () => {
    const rendered = await ValuationRoute({
      params: Promise.resolve({ locale: 'en', place: 'krakow~mysliwska~60~3' }),
    });

    const html = renderToStaticMarkup(rendered);
    const block = html.match(
      /<script type="application\/ld\+json">([\s\S]*?)<\/script>/
    );
    expect(block).not.toBeNull();

    const document = JSON.parse(block?.[1] ?? '{}') as {
      '@graph': Record<string, unknown>[];
    };
    const residence = document['@graph'].find((node) => node['@type'] === 'Residence');
    expect(residence).toMatchObject({ numberOfRooms: 3 });

    const offer = document['@graph'].find((node) => node['@type'] === 'Offer');
    expect(offer).toMatchObject({ price: 959182, priceCurrency: 'PLN' });
  });

  it('carries no offer for an answer the register could not price', async () => {
    (serverApi.fetchServerValuation as jest.Mock).mockResolvedValue(null);

    const rendered = await ValuationRoute({
      params: Promise.resolve({ locale: 'en', place: 'krakow~mysliwska~60~3' }),
    });

    const html = renderToStaticMarkup(rendered);
    expect(html).not.toContain('application/ld+json');
  });
});
