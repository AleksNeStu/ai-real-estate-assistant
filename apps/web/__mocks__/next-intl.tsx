/* eslint-disable @typescript-eslint/no-require-imports */
import React from 'react';

/**
 * The next-intl mock for the test environment.
 *
 * It used to return the raw translation key, which worked only while every
 * page heading was a hard-coded English string in the markup. Now that the
 * headings come from the locale files, the mock resolves the real `en`
 * catalogue — the tests then assert the copy the user actually sees, and a
 * missing key still shows up as the key instead of silently passing.
 */
const catalog = require('../messages/en.json') as Record<string, unknown>;

function resolve(namespace: string | undefined, key: string): unknown {
  const path = namespace ? `${namespace}.${key}` : key;
  return path.split('.').reduce<unknown>(
    (acc, part) =>
      acc && typeof acc === 'object' ? (acc as Record<string, unknown>)[part] : undefined,
    catalog
  );
}

function interpolate(template: string, params?: Record<string, unknown>): string {
  if (!params) return template;
  return template.replace(/\{(\w+)\}/g, (match, name) =>
    name in params ? String(params[name]) : match
  );
}

const translator =
  (namespace?: string) => (key: string, params?: Record<string, unknown>) => {
    const value = resolve(namespace, key);
    return typeof value === 'string' ? interpolate(value, params) : key;
  };

/**
 * A stable translator per namespace, the way next-intl hands it out. A fresh
 * function on every render would make every `useCallback` that depends on `t`
 * change identity, and a `useEffect` that depends on that callback would then
 * loop forever.
 */
const translatorCache = new Map<string, ReturnType<typeof translator>>();
const stableTranslator = (namespace?: string) => {
  const cacheKey = namespace ?? '';
  let cached = translatorCache.get(cacheKey);
  if (!cached) {
    cached = translator(namespace);
    translatorCache.set(cacheKey, cached);
  }
  return cached;
};

export const useTranslations = stableTranslator;
export const getTranslations = async (namespace?: string) => stableTranslator(namespace);
export const useLocale = () => 'en';
export const useMessages = () => catalog;
export const useFormatter = () => ({
  number: (value: number) => String(value),
  dateTime: (value: Date) => value.toISOString(),
});
export const NextIntlClientProvider = ({ children }: { children: React.ReactNode }) => (
  <>{children}</>
);
