import type { Locale } from '@/i18n/config';
import { SITE_URL } from './site';

/**
 * Build a Schema.org @graph JSON-LD structure for the AI Real Estate Assistant.
 *
 * Contains exactly one each of:
 *   - Organization  — the project maintainer entity
 *   - WebSite       — the canonical deployed application
 *   - SoftwareApplication — the OSS product itself
 *
 * All @id anchors use the SITE_URL origin for stability.
 * Claims are limited to facts visible in the README and package metadata:
 *   MIT license (free / price "0"), GitHub source, 9 supported languages,
 *   and PropVector AI as a sameAs related link — NOT the canonical app URL.
 *
 * @param locale — the current locale (unused in v1; reserved for i18n expansion)
 */
export function buildStructuredData(_locale: Locale): Record<string, unknown> {
  const origin = SITE_URL.origin;
  const githubUrl = 'https://github.com/AleksNeStu/ai-real-estate-assistant';
  const propVectorUrl = 'https://propvectorai.com';
  const liveDemoUrl = 'https://realestate-web-dz1y.onrender.com';

  // Stable @id anchors under the Render canonical origin
  const orgId = `${origin}/#organization`;
  const siteId = `${origin}/#website`;
  const appId = `${origin}/#softwareapplication`;

  const supportedLanguages = [
    'English',
    'Polish',
    'Russian',
    'German',
    'Spanish',
    'Italian',
    'Portuguese',
    'Turkish',
    'Ukrainian',
  ];

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
        inLanguage: 'en',
        isAccessibleForFree: true,
        keywords: 'real estate,property search,AI,chatbot,conversational AI',
      },
      {
        '@type': 'SoftwareApplication',
        '@id': appId,
        name: 'AI Real Estate Assistant',
        description:
          'Open-source conversational AI platform for property search and market analytics. Built with FastAPI, Next.js, and ChromaDB.',
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
    ],
  };
}
