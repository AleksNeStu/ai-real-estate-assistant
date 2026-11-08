import type { Locale } from '@/i18n/config';
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
      answer:
        'The live demo uses simulated AI responses and curated mock data for instant exploration — no signup needed. A production deployment with real listings requires API keys and your own data source.',
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
      answer:
        'OpenAI, Anthropic, Google, Grok, DeepSeek, and local Ollama. Automatic fallback chain ensures reliability. Provider selection is per-task and per-user with priority cascade.',
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
