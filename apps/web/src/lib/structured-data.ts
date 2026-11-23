import type { Locale } from '@/i18n/config';
import type { Property } from './types';
import { SITE_URL } from './site';

/**
 * Localized strings of the JSON-LD document.
 *
 * The lib stays free of any i18n dependency: the caller reads the strings
 * from the message catalogue and hands them over as `copy`. Without a copy
 * the English defaults are used, which keeps the document valid in every
 * locale even if a translation is missing.
 */
export interface StructuredDataCopy {
  description: string;
  keywords: string;
  /** The nine supported languages, named in the reader's language. */
  languages: string[];
  faq: { question: string; answer: string }[];
}

const DEFAULT_COPY: StructuredDataCopy = {
  description:
    'Open-source conversational AI platform for property search and market analytics. Built with FastAPI, Next.js, and ChromaDB.',
  keywords: 'real estate,property search,AI,chatbot,conversational AI',
  languages: [
    'English',
    'Polish',
    'Russian',
    'German',
    'Spanish',
    'Italian',
    'Portuguese',
    'Turkish',
    'Ukrainian',
  ],
  faq: [
    {
      question: 'What is AI Real Estate Assistant?',
      answer:
        'An open-source conversational AI platform for property search, analytics, and market insights. Ask in natural language — for example "2-bedroom apartment in Kraków under 500k" — and get matched listings. Built with FastAPI, Next.js, and ChromaDB.',
    },
    {
      question: 'How is it different from Zillow, Rightmove, or Idealista?',
      answer:
        'It is AI-first and conversational rather than filter-first. The natural-language interface, hybrid semantic + keyword search, multi-provider LLM fallback chain, and self-hostable MIT-licensed stack make it a developer-friendly alternative for building custom property experiences.',
    },
    {
      question: 'Can I self-host it?',
      answer:
        'Yes. MIT-licensed with Docker Compose, a 5-minute quickstart, and full source on GitHub. Add your own LLM API keys (OpenAI, Anthropic, Google, Grok, DeepSeek, or local Ollama) and ChromaDB-backed data.',
    },
    {
      question: 'Is the live demo real?',
      // The demo answers with a real model, and the valuation behind it comes
      // from the official register of notarial prices — the seeded catalogue is
      // the browse surface, not a feed of live listings. Say which is which.
      answer:
        'The live demo answers with a real language model — the deployed instance runs MiniMax — and its valuation comes from the official register of notarial transaction prices (Rejestr Cen Nieruchomości), free by law since 13 February 2026: every estimate shows the comparable sales, the period and the comparison area behind it. The 250-property seeded catalogue is the browse surface, not a live listing feed.',
    },
    {
      question: 'What is the difference from PropVector AI?',
      answer:
        'PropVector AI (propvectorai.com) is a hosted SaaS tier built on this open-source codebase, with managed accounts, live data feeds, AI CRM, and enterprise capabilities. The repository stays open-core: the engine remains free, while commercial features live in the hosted product.',
    },
    {
      question: 'Which languages are supported?',
      answer:
        '9 languages for the UI and chat: English, Polish, Russian, German, Spanish, Italian, Portuguese, Turkish, and Ukrainian. EU AI Act compliance labels are included.',
    },
    {
      question: 'Which LLM providers are supported?',
      // The registry carries seventeen, not the six the answer used to name.
      // A count that is wrong here is the same lie the FAQ told about the demo.
      answer:
        '17 — OpenAI, Anthropic, Google, Grok, DeepSeek, OpenRouter, Groq, Mistral, Qwen, ZAI, Moonshot, OpenCode, Together AI, Fireworks AI, HuggingFace, MiniMax, and local Ollama. Automatic fallback chain ensures reliability. Provider selection is per-task and per-user with priority cascade.',
    },
    {
      question: 'Is there a hosted version with real data?',
      answer:
        'Yes — PropVector AI (propvectorai.com) offers hosted tiers with live data, managed accounts, and enterprise capabilities. The open-source repo stays focused on the core engine and a self-hostable demo experience.',
    },
  ],
};

/**
 * Build a Schema.org @graph JSON-LD structure for the AI Real Estate Assistant.
 *
 * Contains exactly one each of:
 *   - Organization  — the project maintainer entity
 *   - WebSite       — the canonical deployed application
 *   - SoftwareApplication — the OSS product itself
 *   - FAQPage       — the product FAQ, in the language of the reader
 *
 * All @id anchors use the SITE_URL origin for stability.
 * Claims are limited to facts visible in the README and package metadata:
 *   MIT license (free / price "0"), GitHub source, 9 supported languages,
 *   and PropVector AI as a sameAs related link — NOT the canonical app URL.
 *
 * @param locale — the current locale (BCP-47 two-letter tag)
 * @param copy — localized description, keywords, language names and FAQ
 */
export function buildStructuredData(
  locale: Locale,
  copy: Partial<StructuredDataCopy> = {}
): Record<string, unknown> {
  const c: StructuredDataCopy = { ...DEFAULT_COPY, ...copy };
  const origin = SITE_URL.origin;
  const githubUrl = 'https://github.com/AleksNeStu/ai-real-estate-assistant';
  const propVectorUrl = 'https://propvectorai.com';
  // The live demo IS the canonical origin — the app is served from the same
  // host the structured data describes, so this follows SITE_URL instead of
  // carrying a second hard-coded hostname that can drift from it.
  const liveDemoUrl = origin;

  // Stable @id anchors under the canonical origin
  const orgId = `${origin}/#organization`;
  const siteId = `${origin}/#website`;
  const appId = `${origin}/#softwareapplication`;

  const supportedLanguages = c.languages;

  return {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'Organization',
        '@id': orgId,
        name: 'AI Real Estate Assistant',
        url: liveDemoUrl,
        sameAs: [githubUrl, propVectorUrl],
      },
      {
        '@type': 'WebSite',
        '@id': siteId,
        name: 'AI Real Estate Assistant',
        url: liveDemoUrl,
        inLanguage: locale,
        isAccessibleForFree: true,
        keywords: c.keywords,
      },
      {
        '@type': 'SoftwareApplication',
        '@id': appId,
        name: 'AI Real Estate Assistant',
        description: c.description,
        applicationCategory: 'BusinessApplication',
        operatingSystem: 'Web',
        url: liveDemoUrl,
        codeRepository: githubUrl,
        availableLanguage: supportedLanguages,
        offers: {
          '@type': 'Offer',
          price: '0',
          priceCurrency: 'EUR',
          availability: 'https://schema.org/OnlineOnly',
        },
        license: 'https://spdx.org/licenses/MIT',
      },
      {
        '@type': 'FAQPage',
        '@id': `${origin}/#faq`,
        inLanguage: locale,
        mainEntity: c.faq.map(({ question, answer }) => ({
          '@type': 'Question',
          name: question,
          acceptedAnswer: {
            '@type': 'Answer',
            text: answer,
          },
        })),
      },
    ],
  };
}

/**
 * The structured data of ONE listing.
 *
 * The site-level document (above) describes the product. A listing page
 * describes a flat: where it is, what it is, what it costs. An answer engine
 * asked "a two-room apartment in Kraków under 500k" can only quote a page
 * that says so in a form it can read - and a search engine can only rank a
 * page whose subject it can identify.
 *
 * The graph carries:
 *   - Property     — the listing itself, with its address, its geo position
 *                    and its offer
 *   - Offer        — the price, the currency and what the price is (a rent
 *                    or a sale), which is the field a buyer filters on
 *   - BreadcrumbList — where the listing sits in the site
 *
 * Everything is taken from the listing the page already shows. Nothing is
 * invented: a listing without a price carries no offer, and a listing without
 * a position carries no geo.
 */
export function buildPropertyStructuredData(
  property: Property,
  options: { url: string; locale: string },
): Record<string, unknown> {
  const { url, locale } = options;
  const origin = SITE_URL.origin;

  const addressParts = [
    property.address,
    property.neighborhood,
    property.district,
    property.city,
    property.region,
    property.country,
  ].filter((part): part is string => Boolean(part));

  const propertyNode: Record<string, unknown> = {
    '@type': 'Property',
    '@id': `${url}#property`,
    name: property.title || `${property.property_type} in ${property.city}`,
    description: property.description || undefined,
    url,
    inLanguage: locale,
  };

  if (addressParts.length) {
    propertyNode.address = {
      '@type': 'PostalAddress',
      streetAddress: property.address,
      addressLocality: property.city,
      addressRegion: property.region,
      addressCountry: property.country,
    };
  }

  if (typeof property.latitude === 'number' && typeof property.longitude === 'number') {
    propertyNode.geo = {
      '@type': 'GeoCoordinates',
      latitude: property.latitude,
      longitude: property.longitude,
    };
  }

  if (typeof property.rooms === 'number') {
    propertyNode.numberOfRooms = property.rooms;
  }
  if (typeof property.bathrooms === 'number') {
    propertyNode.numberOfBathroomsTotal = property.bathrooms;
  }
  if (typeof property.area_sqm === 'number') {
    propertyNode.floorSize = {
      '@type': 'QuantitativeValue',
      value: property.area_sqm,
      unitCode: 'MTK',
    };
  }
  if (typeof property.year_built === 'number') {
    propertyNode.yearBuilt = property.year_built;
  }
  if (typeof property.floor === 'number') {
    propertyNode.floorLevel = property.floor;
  }
  if (property.property_type) {
    propertyNode.accommodationType = property.property_type;
  }

  if (typeof property.price === 'number') {
    propertyNode.offers = {
      '@type': 'Offer',
      price: property.price,
      priceCurrency: property.currency || 'PLN',
      availability: 'https://schema.org/InStock',
      businessFunction:
        property.listing_type === 'sale'
          ? 'http://purl.org/goodrelations/v1#Sell'
          : 'http://purl.org/goodrelations/v1#LeaseOut',
      url,
    };
  }

  return {
    '@context': 'https://schema.org',
    '@graph': [
      propertyNode,
      {
        '@type': 'BreadcrumbList',
        '@id': `${url}#breadcrumb`,
        itemListElement: [
          {
            '@type': 'ListItem',
            position: 1,
            name: 'Search',
            item: `${origin}/${locale}/search`,
          },
          {
            '@type': 'ListItem',
            position: 2,
            name: property.city,
            item: `${origin}/${locale}/city-overview`,
          },
          {
            '@type': 'ListItem',
            position: 3,
            name: property.title || property.id || 'Property',
            item: url,
          },
        ],
      },
    ],
  };
}

/**
 * The structured data of ONE valuation.
 *
 * The listing page describes a flat that is for sale. A valuation page
 * describes a place and what the people who bought there paid for it - and
 * the graph says so in the form an answer engine can read:
 *
 *   - Residence — the place: its address, its size, its number of rooms
 *   - Offer     — the estimate: the price, the currency, and the place it
 *                 is an offer for
 *   - BreadcrumbList — where the answer sits in the site
 *
 * The price comes from the register, so it is the register's number and not
 * an asking price. When the register could not price the place there is no
 * offer node at all - a page that carries a price it does not have is worse
 * than a page that carries none.
 */
export function buildValuationStructuredData(
  valuation: {
    estimated_value?: number | null;
    currency?: string | null;
    comparison_area?: string | null;
    sample_size?: number | null;
    period_start?: string | null;
    period_end?: string | null;
  },
  subject: { city: string; street?: string | null; area_sqm?: number | null; rooms?: number | null },
  options: { url: string; locale: string; basis?: string },
): Record<string, unknown> {
  const { url, locale } = options;
  const origin = SITE_URL.origin;
  const street = subject.street?.trim();

  const residenceNode: Record<string, unknown> = {
    '@type': 'Residence',
    '@id': `${url}#residence`,
    name: [street, subject.city].filter(Boolean).join(', '),
    url,
    inLanguage: locale,
  };

  residenceNode.address = {
    '@type': 'PostalAddress',
    streetAddress: street || undefined,
    addressLocality: subject.city,
  };

  if (typeof subject.area_sqm === 'number') {
    residenceNode.floorSize = {
      '@type': 'QuantitativeValue',
      value: subject.area_sqm,
      unitCode: 'MTK',
    };
  }

  if (typeof subject.rooms === 'number') {
    residenceNode.numberOfRooms = subject.rooms;
  }

  const graph: Record<string, unknown>[] = [residenceNode];

  if (typeof valuation.estimated_value === 'number') {
    graph.push({
      '@type': 'Offer',
      '@id': `${url}#offer`,
      price: valuation.estimated_value,
      priceCurrency: valuation.currency || 'PLN',
      url,
      itemOffered: { '@id': `${url}#residence` },
      // The evidence the estimate rests on travels with it: how many sales,
      // and over which period they were registered.
      ...(options.basis ? { description: options.basis } : {}),
    });
  }

  graph.push({
    '@type': 'BreadcrumbList',
    '@id': `${url}#breadcrumb`,
    itemListElement: [
      {
        '@type': 'ListItem',
        position: 1,
        name: 'Valuation',
        item: `${origin}/${locale}/valuation`,
      },
      {
        '@type': 'ListItem',
        position: 2,
        name: valuation.comparison_area || subject.city,
        item: url,
      },
    ],
  });

  return {
    '@context': 'https://schema.org',
    '@graph': graph,
  };
}

/**
 * The structured data of ONE place.
 *
 * The listing page describes a flat that is for sale. The valuation page
 * describes one address and what the people who bought there paid. A place
 * page describes a city or a district and what a square metre costs there -
 * so the graph says so in the form an answer engine can read:
 *
 *   - Place - the place: its name, its address, the numbers it carries
 *   - BreadcrumbList - where the page sits in the site
 *
 * The numbers travel with the node: how many registered sales the figure is
 * measured on and the period they cover. A price per square metre without
 * the sales under it is a claim, and the graph is where a claim is read.
 */
export function buildPlaceStructuredData(
  figures: {
    place: string;
    district?: string | null;
    comparison_area?: string | null;
    median_price_per_sqm?: number | null;
    sample_size?: number | null;
    period_start?: string | null;
    period_end?: string | null;
    currency?: string | null;
  },
  options: { url: string; locale: string; basis?: string },
): Record<string, unknown> {
  const { url, locale } = options;
  const origin = SITE_URL.origin;
  const name = [figures.district, figures.place].filter(Boolean).join(', ');

  const placeNode: Record<string, unknown> = {
    '@type': 'Place',
    '@id': `${url}#place`,
    name,
    url,
    inLanguage: locale,
    address: {
      '@type': 'PostalAddress',
      addressLocality: figures.place,
    },
  };

  if (typeof figures.median_price_per_sqm === 'number') {
    placeNode.priceRange = `${figures.currency || 'PLN'} ${figures.median_price_per_sqm} per m²`;
  }

  if (options.basis) {
    placeNode.description = options.basis;
  }

  return {
    '@context': 'https://schema.org',
    '@graph': [
      placeNode,
      {
        '@type': 'BreadcrumbList',
        '@id': `${url}#breadcrumb`,
        itemListElement: [
          {
            '@type': 'ListItem',
            position: 1,
            name: 'Valuation',
            item: `${origin}/${locale}/valuation`,
          },
          {
            '@type': 'ListItem',
            position: 2,
            name,
            item: url,
          },
        ],
      },
    ],
  };
}
