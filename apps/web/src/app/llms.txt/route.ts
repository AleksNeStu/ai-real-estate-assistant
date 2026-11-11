import { serverApiUrl } from '@/lib/api/server';
import { LLMS_TXT_BASE } from '@/lib/llms-txt';
import { LOCALES } from '@/lib/metadata';
import { absoluteUrl } from '@/lib/site';

/**
 * The llms.txt route.
 *
 * WHY A ROUTE AND NOT A FILE
 *
 * The document used to be a static file in `public/`. A static file can only
 * say what the author knew when it was written. An answer engine that asks
 * "what does this deployment actually hold?" needs the two facts that change
 * with the instance: the routes that are live, and the catalogue. Both are
 * read here, at request time, from the running deployment.
 *
 * The hand-written half stays in `@/lib/llms-txt` - what the product IS, what
 * it is for, what it is not for. This route adds what the instance IS.
 */

/** The public routes, in the order a reader should meet them. */
const ROUTES = [
  ['/', 'The landing page: what the product is, and the way into it.'],
  ['/search', 'Natural-language property search - the main way in.'],
  ['/chat', 'The assistant: multi-turn questions about properties and markets.'],
  ['/city-overview', 'Listing counts and prices for the cities of the catalogue.'],
  ['/market-trends', 'Price history, listing volume and market indicators per city.'],
  ['/valuation', 'Modelled price range and a multi-year forecast for an address.'],
  ['/tools', 'The financial calculators: mortgage, rent-vs-buy, ROI, TCO.'],
  ['/agents', 'The agent directory of the deployment.'],
  ['/knowledge', 'The knowledge base: documents and the questions asked of them.'],
  ['/showcase', 'What the assistant can do, end to end, with real forks.'],
] as const;

/**
 * The catalogue of this deployment: how many listings it holds, in which
 * cities, and a few of them by name.
 */
/**
 * The size of the catalogue, from the catalogue's own statistics.
 *
 * A page of five listings is not the size of a catalogue: the number
 * the document states has to be the number the deployment holds.
 */
async function catalogueStats(): Promise<
  { total: number; cities: { name: string; count: number }[] } | null
> {
  try {
    const response = await fetch(`${serverApiUrl()}/catalogue/stats`, {
      headers: { Accept: 'application/json' },
      next: { revalidate: 3600 },
    });
    if (!response.ok) return null;
    const data = (await response.json()) as {
      total?: number;
      cities?: { name: string; count: number }[];
    };
    return {
      total: typeof data.total === 'number' ? data.total : 0,
      cities: Array.isArray(data.cities) ? data.cities : [],
    };
  } catch {
    return null;
  }
}

async function catalogueSection(): Promise<string> {
  const empty = [
    '## The catalogue of this deployment',
    '',
    'The catalogue could not be read when this document was served. The API is',
    'at `/api/v1/properties`.',
    '',
  ].join('\n');

  try {
    const response = await fetch(`${serverApiUrl()}/properties?limit=5`, {
      headers: { Accept: 'application/json' },
      next: { revalidate: 3600 },
    });
    if (!response.ok) return empty;

    const data = (await response.json()) as {
      properties?: {
        id?: string;
        title?: string;
        city?: string;
        price?: number;
        currency?: string;
        rooms?: number;
      }[];
      has_more?: boolean;
    };
    const properties = data?.properties ?? [];
    if (!properties.length) return empty;

    const stats = await catalogueStats();
    const total = stats?.total ?? properties.length;
    const cities = stats?.cities ?? [];
    const cityLine = cities.length
      ? ` in ${cities.map((city) => `${city.name} (${city.count})`).join(', ')}`
      : '';
    const lines = properties.map((property) => {
      const where = property.city ?? '';
      const price =
        typeof property.price === 'number'
          ? ` — ${property.price.toLocaleString('en-US')} ${property.currency ?? ''}`
          : '';
      const rooms = property.rooms ? `, ${property.rooms} rooms` : '';
      return `- [${property.title ?? property.id}](${absoluteUrl(`/pl/property/${property.id}`)}) — ${where}${rooms}${price}`;
    });

    return [
      '## The catalogue of this deployment',
      '',
      `This deployment holds ${total} listings${cityLine}. A few of them:`,
      '',
      ...lines,
      '',
      `The whole catalogue: ${absoluteUrl('/pl/search')}.`,
      '',
    ].join('\n');
  } catch {
    return empty;
  }
}

export const dynamic = 'force-dynamic';

export async function GET(): Promise<Response> {
  const routes = ROUTES.map(([path, description]) => {
    const line = path === '/' ? '- [The landing page](/)' : `- [${path}](${absoluteUrl(`/pl${path}`)})`;
    return `${line}: ${description}`;
  });

  const languages = LOCALES.map((locale) => `- ${locale}: ${absoluteUrl(`/${locale}`)}`).join('\n');

  const body = [
    LLMS_TXT_BASE.trimEnd(),
    '',
    '## The live routes of this deployment',
    '',
    ...routes,
    '',
    '## The languages',
    '',
    languages,
    '',
    await catalogueSection(),
  ].join('\n');

  return new Response(body, {
    headers: {
      'Content-Type': 'text/plain; charset=utf-8',
      'Cache-Control': 'public, max-age=3600, stale-while-revalidate=86400',
    },
  });
}
