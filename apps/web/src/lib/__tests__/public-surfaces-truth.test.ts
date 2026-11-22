import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { buildStructuredData } from '../structured-data';
import { LLMS_TXT_BASE } from '../llms-txt';

/**
 * The three public surfaces — the FAQ JSON-LD, the message catalogues it is
 * built from, and llms.txt — have to agree with what the deployment actually
 * does.
 *
 * They used to say the demo answers with simulated responses over mock data.
 * It does not: the deployed instance answers with a real model (MiniMax), and
 * the valuation comes from the official register of notarial transaction
 * prices. What is still not live is a listing feed, and the seeded catalogue
 * is still only a browse surface.
 *
 * These tests are the drift guard. They read the backend's provider registry
 * too, because "16 providers" is exactly the kind of number that rots: the
 * registry grew a provider and the public copy did not.
 */

const MESSAGES_DIR = join(process.cwd(), 'messages');

/** The backend's provider registry — the list the public copy has to match. */
const PROVIDER_REGISTRY = join(process.cwd(), '..', 'api', 'models', 'provider_factory.py');

/** How a provider key is written in the public copy. */
const PROVIDER_NAMES: Record<string, string> = {
  openai: 'OpenAI',
  anthropic: 'Anthropic',
  google: 'Google',
  grok: 'Grok',
  deepseek: 'DeepSeek',
  openrouter: 'OpenRouter',
  groq: 'Groq',
  mistral: 'Mistral',
  qwen: 'Qwen',
  zai: 'ZAI',
  moonshot: 'Moonshot',
  opencode: 'OpenCode',
  together: 'Together AI',
  fireworks: 'Fireworks AI',
  huggingface: 'HuggingFace',
  ollama: 'local Ollama',
  minimax: 'MiniMax',
};

/** The wording a locale uses for the providers it does not translate. */
const PROVIDER_NAMES_BY_LOCALE: Record<string, Record<string, string>> = {
  en: {},
  pl: { ollama: 'lokalny Ollama' },
};

function message(locale: string): Record<string, unknown> {
  const raw = JSON.parse(readFileSync(join(MESSAGES_DIR, `${locale}.json`), 'utf-8')) as Record<
    string,
    unknown
  >;
  return raw;
}

function faqAnswer(locale: string): string {
  const catalogue = message(locale);
  const seo = catalogue.seo as Record<string, unknown>;
  const structuredData = seo.structuredData as Record<string, unknown>;
  const faq = structuredData.faq as Record<string, string>;
  return faq.a4;
}

function faqProviderAnswer(locale: string): string {
  const catalogue = message(locale);
  const seo = catalogue.seo as Record<string, unknown>;
  const structuredData = seo.structuredData as Record<string, unknown>;
  const faq = structuredData.faq as Record<string, string>;
  return faq.a7;
}

/** The provider keys the backend registry declares. */
function registryProviders(): string[] {
  const source = readFileSync(PROVIDER_REGISTRY, 'utf-8');
  const keys = [...source.matchAll(/"([a-z0-9_]+)":\s*"models\.providers\.[a-z0-9_]+"/g)].map(
    (match) => match[1]
  );
  return [...new Set(keys)];
}

/** The provider names the llms.txt FAQ answer lists, without the "and". */
function llmsProviderAnswer(): { count: number; names: string[] } {
  const line = LLMS_TXT_BASE.match(/A: (\d+) — (OpenAI.+?)\. Automatic fallback chain\./);
  if (!line) throw new Error('The llms.txt FAQ no longer names its LLM providers.');
  return {
    count: Number(line[1]),
    names: line[2]
      .split(', ')
      .map((name) => name.replace(/^and /, ''))
      .filter(Boolean),
  };
}

describe('the public surfaces do not contradict the deployment', () => {
  describe('the FAQ JSON-LD', () => {
    const graph = buildStructuredData('en')['@graph'] as Record<string, unknown>[];
    const faq = graph.find((node) => node['@type'] === 'FAQPage');
    const answers = (
      faq!.mainEntity as { acceptedAnswer: { text: string } }[]
    ).map((question) => question.acceptedAnswer.text);

    it('no longer says the demo answers with simulated responses', () => {
      expect(answers.join(' ')).not.toMatch(/simulated AI responses|mock data/i);
    });

    it('says the demo answers with a real model', () => {
      expect(answers.join(' ')).toMatch(/MiniMax/);
    });

    it('names the official register of notarial transaction prices', () => {
      expect(answers.join(' ')).toMatch(/Rejestr Cen Nieruchomości/);
    });

    it('keeps the seeded catalogue apart from a live listing feed', () => {
      const answer = answers.find((text) => text.includes('Rejestr Cen Nieruchomości'));
      expect(answer).toBeDefined();
      expect(answer).toMatch(/catalogue/i);
      expect(answer).toMatch(/not a live listing feed/i);
    });
  });

  describe('the message catalogues the JSON-LD is built from', () => {
    it('the English catalogue carries the same answer', () => {
      expect(faqAnswer('en')).toMatch(/MiniMax/);
      expect(faqAnswer('en')).toMatch(/Rejestr Cen Nieruchomości/);
      expect(faqAnswer('en')).not.toMatch(/simulated AI responses|mock data/i);
    });

    it('the Polish catalogue carries the same claim in Polish', () => {
      expect(faqAnswer('pl')).toMatch(/MiniMax/);
      expect(faqAnswer('pl')).toMatch(/Rejestr Cen Nieruchomości/);
      expect(faqAnswer('pl')).not.toMatch(/symulowanych odpowiedzi AI/i);
    });

    it('the Polish answer is a translation, not the English string', () => {
      expect(faqAnswer('pl')).not.toBe(faqAnswer('en'));
    });

    it('both catalogues name the seventeen providers', () => {
      for (const locale of ['en', 'pl']) {
        const answer = faqProviderAnswer(locale);
        const overrides = PROVIDER_NAMES_BY_LOCALE[locale] ?? {};
        expect(answer).toMatch(/^17 — /);
        for (const [key, name] of Object.entries(PROVIDER_NAMES)) {
          expect(answer).toContain(overrides[key] ?? name);
        }
      }
    });
  });

  describe('llms.txt', () => {
    it('no longer says the demo answers with simulated responses', () => {
      expect(LLMS_TXT_BASE).not.toMatch(/simulated AI responses/i);
    });

    it('says the demo answers with a real model and names the register', () => {
      expect(LLMS_TXT_BASE).toMatch(/MiniMax/);
      expect(LLMS_TXT_BASE).toMatch(/Rejestr Cen Nieruchomości/);
    });

    it('separates the live register from the missing listing feed', () => {
      expect(LLMS_TXT_BASE).toMatch(/No listing feed out of the box/i);
      expect(LLMS_TXT_BASE).toMatch(/register of notarial transaction prices, not a stream of listings/i);
    });

    it('names every provider of the backend registry', () => {
      for (const key of registryProviders()) {
        const name = PROVIDER_NAMES[key];
        expect(name).toBeDefined();
        expect(LLMS_TXT_BASE).toContain(name);
      }
    });

    it('counts the providers the backend registry holds', () => {
      const answer = llmsProviderAnswer();
      expect(answer.count).toBe(registryProviders().length);
      expect(answer.names).toHaveLength(registryProviders().length);
    });
  });
});
