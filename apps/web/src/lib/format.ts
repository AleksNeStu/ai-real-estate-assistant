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
 * The money shape the calculators print.
 *
 * The sign stands outside the currency symbol ("-$1,200", not "$-1,200") -
 * the same sign the currency format prints - in the shape these surfaces
 * have always used: the symbol in front, and the digits grouped the way the
 * runtime groups them. A difference adds its own plus.
 */
export function formatSignedMoney(value?: number | null): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '';
  const sign = value < 0 ? '-' : '';
  return `${sign}$${Math.abs(value).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}

/**
 * The label of a map pin: the price the row next to it shows.
 *
 * A pin is a small space, so the price is shortened - but it must stay the
 * SAME price, not a rounded one. The landing's hero used to print the number
 * in thousands with no magnitude check, so 322 000 zł read as "322k" and
 * 4 100 zł read as "4k" while the row underneath said "4 100 zł". The first
 * fix carried the currency into the chip ("PLN 2.1K") - which still states a
 * DIFFERENT price: a 2 100 zł listing reads as 2.1K.
 *
 * So the pin follows the map's own rule, the one the search popup already
 * uses: the exact price, and the compact form only for the prices that are
 * genuinely too long for a chip. One price, one spelling.
 */
export function formatMapPinPrice(
  value?: number | null,
  currency = 'PLN',
  locale = 'pl-PL'
): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  if (value >= 1_000_000) return formatCompactPrice(value, currency, locale) || '—';
  return formatPrice(value, currency, locale);
}
