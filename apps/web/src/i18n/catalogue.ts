/**
 * The catalogue a locale renders.
 *
 * The request config and the layout both ask this module for the messages, so
 * the server components and the client components read the same object: the
 * English catalogue with the locale's own words wherever the locale carries
 * them. A frozen locale therefore never renders a key path — it renders the
 * English wording of the key it did not translate.
 *
 * The result is cached per locale: the message files are static for the
 * lifetime of a build, and the merge walks every leaf of the catalogue.
 */

import enMessages from '../../messages/en.json';
import { isValidLocale } from './config';
import { mergeMessages, type Messages } from './merge';

const cache = new Map<string, Messages>();

/**
 * The merged catalogue of a locale.
 *
 * An unknown locale falls back to Polish, the same way the request config
 * resolves one.
 */
export async function catalogueFor(locale: string): Promise<Messages> {
  const key = isValidLocale(locale) ? locale : 'pl';

  const cached = cache.get(key);
  if (cached) return cached;

  const english = enMessages as Messages;
  let catalogue: Messages;

  if (key === 'en') {
    catalogue = english;
  } else {
    const localeMessages = (await import(`../../messages/${key}.json`)).default as Messages;
    catalogue = mergeMessages(english, localeMessages);
  }

  cache.set(key, catalogue);
  return catalogue;
}
