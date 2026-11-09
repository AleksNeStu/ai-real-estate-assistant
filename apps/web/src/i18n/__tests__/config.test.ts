import { describe, it, expect } from '@jest/globals';
import {
  locales,
  defaultLocale,
  localeNames,
  localeFlags,
  frozenLocales,
  isValidLocale,
  maintainedLocales,
  type Locale,
} from '../config';

describe('i18n config', () => {
  describe('locales', () => {
    it('should contain supported locales', () => {
      expect(locales).toContain('pl');
      expect(locales).toContain('en');
      expect(locales).toContain('ru');
      expect(locales).toContain('de');
      expect(locales).toContain('es');
      expect(locales).toContain('uk');
    });

    it('should have at least 9 locales', () => {
      expect(locales.length).toBeGreaterThanOrEqual(9);
    });

    it('should be readonly array', () => {
      expect(Array.isArray(locales)).toBe(true);
    });
  });

  describe('the maintained pair', () => {
    it('is English and Polish', () => {
      expect([...maintainedLocales].sort()).toEqual(['en', 'pl']);
    });

    it('leaves every other locale frozen', () => {
      expect([...frozenLocales].sort()).toEqual(['de', 'es', 'it', 'pt', 'ru', 'tr', 'uk']);
    });

    it('covers every locale exactly once', () => {
      expect([...maintainedLocales, ...frozenLocales].sort()).toEqual([...locales].sort());
    });
  });

  describe('defaultLocale', () => {
    it('should be Polish', () => {
      expect(defaultLocale).toBe('pl');
    });

    it('should be one of the valid locales', () => {
      expect(locales).toContain(defaultLocale);
    });
  });

  describe('localeNames', () => {
    it('should have names for all locales', () => {
      expect(localeNames.pl).toBe('Polski');
      expect(localeNames.en).toBe('English');
      expect(localeNames.ru).toBe('Русский');
    });

    it('should have names for all defined locales', () => {
      locales.forEach((locale) => {
        expect(localeNames[locale]).toBeDefined();
      });
    });
  });

  describe('localeFlags', () => {
    it('should have flags for all locales', () => {
      expect(localeFlags.pl).toBe('🇵🇱');
      expect(localeFlags.en).toBe('🇬🇧');
      expect(localeFlags.ru).toBe('🇷🇺');
    });

    it('should have flags for all defined locales', () => {
      locales.forEach((locale) => {
        expect(localeFlags[locale]).toBeDefined();
      });
    });
  });

  describe('isValidLocale', () => {
    it('should return true for valid locales', () => {
      expect(isValidLocale('pl')).toBe(true);
      expect(isValidLocale('en')).toBe(true);
      expect(isValidLocale('ru')).toBe(true);
      expect(isValidLocale('de')).toBe(true);
      expect(isValidLocale('es')).toBe(true);
      expect(isValidLocale('uk')).toBe(true);
    });

    it('should return false for invalid locales', () => {
      expect(isValidLocale('fr')).toBe(false);
      expect(isValidLocale('zh')).toBe(false);
      expect(isValidLocale('')).toBe(false);
      expect(isValidLocale('PL')).toBe(false); // case-sensitive
    });
  });

  describe('Locale type', () => {
    it('should be a union of locale strings', () => {
      const validLocale: Locale = 'pl';
      expect(typeof validLocale).toBe('string');
    });
  });
});
