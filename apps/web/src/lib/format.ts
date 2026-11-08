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
      maximumFractionDigits: 1,
    }).format(value);
  } catch {
    // An unknown currency code must not take the price down with it.
    return `${new Intl.NumberFormat(resolved).format(value)} ${currency}`;
  }
}
