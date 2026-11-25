export const locales = ['pl', 'en', 'ru', 'de', 'es', 'it', 'pt', 'tr', 'uk'] as const;
export const defaultLocale = 'en' as const;

export type Locale = (typeof locales)[number];

/**
 * The locales the interface is maintained in.
 *
 * English, Polish and Russian are the set the product is written for. English is
 * the default the site opens in — the language every provider, every partner
 * and every AI reader understands — while Polish stays the home market: the
 * demo catalogue and the currency still come from it. Russian was brought back
 * to the maintained set on 2026-11-24 (Task #63): it now carries every key, so
 * a new key lands in these three catalogues only.
 *
 * The other six keep the wording they were given. They still ship: their
 * URLs, their hreflang entries and the language switcher stay, and the merge
 * in `merge.ts` fills whatever they do not carry with the English wording.
 * A feature therefore costs three translations instead of nine.
 */
export const maintainedLocales = ['en', 'pl', 'ru'] as const;

export type MaintainedLocale = (typeof maintainedLocales)[number];

/** The locales that keep their wording and fall back to English. */
export const frozenLocales = locales.filter(
  (locale): locale is Exclude<Locale, MaintainedLocale> =>
    !(maintainedLocales as readonly Locale[]).includes(locale)
);

export const localeNames: Record<Locale, string> = {
  pl: 'Polski',
  en: 'English',
  ru: 'Русский',
  de: 'Deutsch',
  es: 'Español',
  it: 'Italiano',
  pt: 'Português',
  tr: 'Türkçe',
  uk: 'Українська',
};

export const localeFlags: Record<Locale, string> = {
  pl: '🇵🇱',
  en: '🇬🇧',
  ru: '🇷🇺',
  de: '🇩🇪',
  es: '🇪🇸',
  it: '🇮🇹',
  pt: '🇵🇹',
  tr: '🇹🇷',
  uk: '🇺🇦',
};

/** RTL locales that require right-to-left layout */
export const rtlLocales: readonly Locale[] = [] as const;

/** Check if a locale uses RTL layout */
export function isRTL(locale: string): boolean {
  return (rtlLocales as readonly string[]).includes(locale);
}

/**
 * Validates if a string is a valid locale
 */
export function isValidLocale(locale: string): locale is Locale {
  return locales.includes(locale as Locale);
}
