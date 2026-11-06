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
 * @param locale — the current locale (BCP-47 two-letter tag)
 */
export function buildStructuredData(locale: Locale): Record<string, unknown> {
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
        inLanguage: locale,
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
      {
        '@type': 'FAQPage',
        '@id': `${origin}/#faq`,
        inLanguage: 'en',
        mainEntity: [
          {
            '@type': 'Question',
            name: 'What is AI Real Estate Assistant?',
            acceptedAnswer: {
              '@type': 'Answer',
              text: 'An open-source conversational AI platform for property search, analytics, and market insights. Ask in natural language — for example "2-bedroom apartment in Kraków under 500k" — and get matched listings. Built with FastAPI, Next.js, and ChromaDB.',
            },
          },
          {
            '@type': 'Question',
            name: 'How is it different from Zillow, Rightmove, or Idealista?',
            acceptedAnswer: {
              '@type': 'Answer',
              text: 'It is AI-first and conversational rather than filter-first. The natural-language interface, hybrid semantic + keyword search, multi-provider LLM fallback chain, and self-hostable MIT-licensed stack make it a developer-friendly alternative for building custom property experiences.',
            },
          },
          {
            '@type': 'Question',
            name: 'Can I self-host it?',
            acceptedAnswer: {
              '@type': 'Answer',
              text: 'Yes. MIT-licensed with Docker Compose, a 5-minute quickstart, and full source on GitHub. Add your own LLM API keys (OpenAI, Anthropic, Google, Grok, DeepSeek, or local Ollama) and ChromaDB-backed data.',
            },
          },
          {
            '@type': 'Question',
            name: 'Is the live demo real?',
            acceptedAnswer: {
              '@type': 'Answer',
              text: 'The live demo uses simulated AI responses and curated mock data for instant exploration — no signup needed. A production deployment with real listings requires API keys and your own data source.',
            },
          },
          {
            '@type': 'Question',
            name: 'What is the difference from PropVector AI?',
            acceptedAnswer: {
              '@type': 'Answer',
              text: 'PropVector AI (propvectorai.com) is a hosted SaaS tier built on this open-source codebase, with managed accounts, live data feeds, AI CRM, and enterprise capabilities. The repository stays open-core: the engine remains free, while commercial features live in the hosted product.',
            },
          },
          {
            '@type': 'Question',
            name: 'Which languages are supported?',
            acceptedAnswer: {
              '@type': 'Answer',
              text: '9 languages for the UI and chat: English, Polish, Russian, German, Spanish, Italian, Portuguese, Turkish, and Ukrainian. EU AI Act compliance labels are included.',
            },
          },
          {
            '@type': 'Question',
            name: 'Which LLM providers are supported?',
            acceptedAnswer: {
              '@type': 'Answer',
              text: 'OpenAI, Anthropic, Google, Grok, DeepSeek, and local Ollama. Automatic fallback chain ensures reliability. Provider selection is per-task and per-user with priority cascade.',
            },
          },
          {
            '@type': 'Question',
            name: 'Is there a hosted version with real data?',
            acceptedAnswer: {
              '@type': 'Answer',
              text: 'Yes — PropVector AI (propvectorai.com) offers hosted tiers with live data, managed accounts, and enterprise capabilities. The open-source repo stays focused on the core engine and a self-hostable demo experience.',
            },
          },
        ],
      },
    ],
  };
}
