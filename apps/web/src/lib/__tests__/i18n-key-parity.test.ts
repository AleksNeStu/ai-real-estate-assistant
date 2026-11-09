import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';

/**
 * The nine catalogues must carry the same keys.
 *
 * The English catalogue is the source. A locale that misses a key falls back
 * to English at runtime (next-intl does that), which is why the drift was
 * invisible: the interface simply spoke English on some pages. The rule of
 * the project is that a key lands in all nine locales in the same change, and
 * this test is what makes that rule hold.
 */

const MESSAGES_DIR = join(process.cwd(), 'messages');

function leaves(node: unknown, prefix = ''): Set<string> {
  const keys = new Set<string>();
  if (typeof node !== 'object' || node === null) return keys;
  for (const [key, value] of Object.entries(node as Record<string, unknown>)) {
    const path = prefix ? `${prefix}.${key}` : key;
    if (typeof value === 'object' && value !== null) {
      for (const nested of leaves(value, path)) keys.add(nested);
    } else {
      keys.add(path);
    }
  }
  return keys;
}

function catalogue(locale: string): Set<string> {
  const raw = readFileSync(join(MESSAGES_DIR, `${locale}.json`), 'utf-8');
  return leaves(JSON.parse(raw));
}

const locales = readdirSync(MESSAGES_DIR)
  .filter((file) => file.endsWith('.json'))
  .map((file) => file.replace('.json', ''))
  .sort();

describe('the message catalogues', () => {
  it('covers the nine locales of the interface', () => {
    expect(locales).toEqual(['de', 'en', 'es', 'it', 'pl', 'pt', 'ru', 'tr', 'uk']);
  });

  const source = catalogue('en');

  it.each(locales.filter((locale) => locale !== 'en'))('%s carries every key of the English catalogue', (locale) => {
    const target = catalogue(locale);
    const missing = [...source].filter((key) => !target.has(key));
    expect(missing).toEqual([]);
  });

  it.each(locales.filter((locale) => locale !== 'en'))('%s carries no key the English catalogue does not have', (locale) => {
    const target = catalogue(locale);
    const extra = [...target].filter((key) => !source.has(key));
    expect(extra).toEqual([]);
  });
});
