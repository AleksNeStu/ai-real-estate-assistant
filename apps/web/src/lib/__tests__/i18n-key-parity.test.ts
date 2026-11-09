import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { locales } from '../../i18n/config';
import { maintainedLocales } from '../../i18n/policy';
import { mergeMessages, placeholderNames } from '../../i18n/merge';

/**
 * English and Polish are the maintained pair; the other seven catalogues are
 * frozen.
 *
 * A new key lands in `en.json` and `pl.json` only. The frozen catalogues keep
 * the wording they were given and are allowed to lag behind — that is what
 * moves the other seven languages into the backlog instead of making every
 * feature cost nine translations.
 *
 * The merge in `merge.ts` is what makes that safe: whatever a locale renders
 * is the English key set, so a catalogue that lags shows the English wording
 * instead of a key path. These tests hold both halves:
 *
 *   - the maintained pair must carry the same keys, so a change cannot land in
 *     one of them and be forgotten in the other;
 *   - a catalogue must not invent a key the English catalogue does not have,
 *     because the merge would drop it silently;
 *   - and a locale must not name its placeholders differently from English,
 *     because the merge would then fall back to the English wording.
 */

const MESSAGES_DIR = join(process.cwd(), 'messages');

type Catalogue = Record<string, unknown>;

/** Every leaf, with the elements of an array counted separately. */
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

/** Every message, with an array counted as one unit. */
function units(node: unknown, prefix = ''): Set<string> {
  const keys = new Set<string>();
  if (typeof node !== 'object' || node === null) return keys;
  for (const [key, value] of Object.entries(node as Record<string, unknown>)) {
    const path = prefix ? `${prefix}.${key}` : key;
    if (Array.isArray(value)) keys.add(path);
    else if (value && typeof value === 'object') {
      for (const nested of units(value, path)) keys.add(nested);
    } else {
      keys.add(path);
    }
  }
  return keys;
}

function raw(locale: string): Catalogue {
  return JSON.parse(readFileSync(join(MESSAGES_DIR, `${locale}.json`), 'utf-8')) as Catalogue;
}

function catalogue(locale: string): Set<string> {
  return leaves(raw(locale));
}

/** The placeholders of every message of a catalogue, path by path. */
function placeholders(node: unknown, prefix = ''): Map<string, string[]> {
  const found = new Map<string, string[]>();
  if (typeof node !== 'object' || node === null) return found;
  for (const [key, value] of Object.entries(node as Record<string, unknown>)) {
    const path = prefix ? `${prefix}.${key}` : key;
    if (typeof value === 'object' && value !== null) {
      for (const [nestedPath, names] of placeholders(value, path)) found.set(nestedPath, names);
    } else if (typeof value === 'string') {
      found.set(path, placeholderNames(value));
    }
  }
  return found;
}

describe('the message catalogues', () => {
  it('covers the nine locales of the interface', () => {
    expect([...locales].sort()).toEqual(['de', 'en', 'es', 'it', 'pl', 'pt', 'ru', 'tr', 'uk']);
  });

  describe('the maintained pair', () => {
    it.each(maintainedLocales.filter((locale) => locale !== 'en'))(
      '%s carries the keys the English catalogue carries',
      (locale) => {
        const english = catalogue('en');
        const target = catalogue(locale);

        const missing = [...english].filter((key) => !target.has(key));
        expect(missing).toEqual([]);
      }
    );
  });

  describe('every locale', () => {
    it.each(locales)('%s invents no key the English catalogue does not have', (locale) => {
      const english = catalogue('en');
      const target = catalogue(locale);

      const invented = [...target].filter((key) => !english.has(key));
      expect(invented).toEqual([]);
    });

    it.each(locales)('%s names the same placeholders as English', (locale) => {
      const english = placeholders(raw('en'));
      const target = placeholders(raw(locale));

      const mismatched = [...english]
        .filter(([path, names]) => {
          const other = target.get(path);
          return other !== undefined && other.join(',') !== names.join(',');
        })
        .map(([path]) => path);

      expect(mismatched).toEqual([]);
    });
  });

  describe('what a locale renders', () => {
    it.each(locales)('%s renders the English key set', (locale) => {
      const english = raw('en');
      const merged = mergeMessages(english, raw(locale));
      expect(units(merged)).toEqual(units(english));
    });
  });
});
