/**
 * Price and number formatting for the surfaces that show money.
 *
 * The card used to hard-code a dollar sign in front of every price, so a
 * property listed in Polish zloty was displayed in dollars while the
 * mortgage estimate next to it used the property's own currency.
 */

const FALLBACK_LOCALES: Record<string, string> = {
  pl: 'pl-PL',
  en: 'en-US',
  ru: 'ru-RU',
  de: 'de-DE',
  es: 'es-ES',
  it: 'it-IT',
  pt: 'pt-PT',
  tr: 'tr-TR',
  uk: 'uk-UA',
};

export function resolveLocale(locale?: string): string {
  if (!locale) return 'en-US';
  return FALLBACK_LOCALES[locale] ?? locale;
}

/**
 * Formats an amount in the property's own currency.
 *
 * Returns an empty string for missing or invalid values so the caller can
 * decide what to render instead.
 */
export function formatPrice(
  value?: number | null,
  currency = 'USD',
  locale = 'en-US'
): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '';
  const resolved = resolveLocale(locale);
  try {
    return new Intl.NumberFormat(resolved, {
      style: 'currency',
      currency,
      maximumFractionDigits: 0,
    }).format(value);
  } catch {
    // An unknown currency code must not take the price down with it.
    return `${new Intl.NumberFormat(resolved).format(value)} ${currency}`;
  }
}

/**
 * Short form for map popups and tight spaces: 1 250 000 -> 1.3M.
 *
 * The currency is the listing's own, and the placement of the symbol is the
 * locale's: Polish reads "300 tys. zł", English "PLN 300K".
 */
export function formatCompactPrice(
  value?: number | null,
  currency = 'USD',
  locale = 'en-US'
): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '';
  const resolved = resolveLocale(locale);
  try {
    return new Intl.NumberFormat(resolved, {
      style: 'currency',
      currency,
      notation: 'compact',
      // The currency style asks for two decimals by default. The compact
      // notation has no room for them, so without this the same price reads
      // "$300K" on one runtime and "$300.0K" on another - the filters of
      // the map carried both spellings into the tests.
      minimumFractionDigits: 0,
      maximumFractionDigits: 1,
    }).format(value);
  } catch {
    // An unknown currency code must not take the price down with it.
    return `${new Intl.NumberFormat(resolved).format(value)} ${currency}`;
  }
}

/**
 * The label of a map pin: the price, compact, in the visitor's locale.
 *
 * A pin is a small space, so the price is shortened - but it must stay the
 * SAME price the row next to it shows. The landing's hero used to print the
 * number in thousands with no magnitude check, so 322 000 zł read as "322k"
 * and 4 100 zł read as "4k" while the row underneath said "4 100 zł". One
 * price, one spelling: this is the compact currency format the map popups
 * already use, and a missing price reads as a dash rather than as nothing.
 */
export function formatMapPinPrice(
  value?: number | null,
  currency = 'PLN',
  locale = 'en-US'
): string {
  const compact = formatCompactPrice(value, currency, locale);
  return compact || '—';
}
