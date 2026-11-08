import { getRequestConfig } from 'next-intl/server';
import { locales, type Locale } from './config';
import enMessages from '../../messages/en.json';

/**
 * Flattened English catalog. A locale that does not carry a key yet falls back
 * to the English wording instead of breaking the page.
 */
const englishByKey: Record<string, string> = (() => {
  const out: Record<string, string> = {};
  const walk = (node: unknown, prefix: string) => {
    if (!node || typeof node !== 'object') return;
    for (const [key, value] of Object.entries(node as Record<string, unknown>)) {
      const full = prefix ? `${prefix}.${key}` : key;
      if (value && typeof value === 'object') walk(value, full);
      else if (typeof value === 'string') out[full] = value;
    }
  };
  walk(enMessages, '');
  return out;
})();

export default getRequestConfig(async ({ requestLocale }) => {
  // This typically corresponds to the `[locale]` segment
  let locale = await requestLocale;

  // Ensure that a valid locale is used
  if (!locale || !locales.includes(locale as Locale)) {
    locale = 'pl';
  }

  return {
    locale,
    messages: (await import(`../../messages/${locale}.json`)).default,
    getMessageFallback: ({ key, namespace }) => {
      const candidates = namespace ? [`${namespace}.${key}`, key] : [key];
      for (const candidate of candidates) {
        const fallback = englishByKey[candidate];
        if (fallback !== undefined) return fallback;
      }
      return key;
    },
  };
});
