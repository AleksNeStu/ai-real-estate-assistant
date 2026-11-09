export const locales = ['pl', 'en', 'ru', 'de', 'es', 'it', 'pt', 'tr', 'uk'] as const;
export const defaultLocale = 'pl' as const;

export type Locale = (typeof locales)[number];

/**
 * The locales the interface is maintained in.
 *
 * English and Polish are the pair the product is written for. Polish is the
 * home market — the demo catalogue, the currency and the x-default come from
 * it — and English is the language every provider, every partner and every AI
 * reader understands. A new key lands in these two catalogues only.
 *
 * The other seven keep the wording they were given. They still ship: their
 * URLs, their hreflang entries and the language switcher stay, and the merge
 * in `merge.ts` fills whatever they do not carry with the English wording.
 * A feature therefore costs two translations instead of nine.
 */
export const maintainedLocales = ['en', 'pl'] as const;

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
