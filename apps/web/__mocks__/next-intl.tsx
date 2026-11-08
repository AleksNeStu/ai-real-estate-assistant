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
 *
 * The mock also formats ICU messages (plurals, placeholders) itself. It used
 * to hand-roll a naive `{name}` substitution, which silently dropped
 * `{count, plural, one {...} other {...}}` and returned the raw template.
 * The formatter below implements the subset the catalogue actually uses and
 * is verified against the real next-intl/intl-messageformat output.
 *
 * The mock lives outside jest's `next-intl` mapping on purpose: importing
 * `next-intl` here would be circular, and `use-intl` is only a transitive
 * dependency of the app.
 */
const catalog = require('../messages/en.json') as Record<string, unknown>;

function resolve(namespace: string | undefined, key: string): unknown {
  const path = namespace ? `${namespace}.${key}` : key;
  return path
    .split('.')
    .reduce<unknown>(
      (acc, part) =>
        acc && typeof acc === 'object' ? (acc as Record<string, unknown>)[part] : undefined,
      catalog
    );
}

/** Split a message into literal chunks and `{...}` blocks (brace aware). */
function tokenize(message: string): string[] {
  const tokens: string[] = [];
  let buffer = '';
  let depth = 0;
  let current = '';

  for (const char of message) {
    if (char === '{') {
      if (depth === 0) {
        if (buffer) tokens.push(buffer);
        buffer = '';
        current = '';
      }
      depth++;
      current += char;
      continue;
    }
    if (char === '}') {
      depth--;
      current += char;
      if (depth === 0) {
        tokens.push(current);
        current = '';
      }
      continue;
    }
    if (depth === 0) {
      buffer += char;
    } else {
      current += char;
    }
  }

  if (buffer) tokens.push(buffer);
  if (current) tokens.push(current);
  return tokens;
}

/** Parse `name, type, style` out of a `{...}` block. */
function parseArgument(block: string): {
  name: string;
  type: string;
  style: string;
} {
  const inner = block.slice(1, -1);
  const comma = inner.indexOf(',');
  if (comma === -1) return { name: inner.trim(), type: 'simple', style: '' };
  const name = inner.slice(0, comma).trim();
  const rest = inner.slice(comma + 1);
  const nextComma = rest.indexOf(',');
  if (nextComma === -1) return { name, type: rest.trim(), style: '' };
  return { name, type: rest.slice(0, nextComma).trim(), style: rest.slice(nextComma + 1).trim() };
}

/** Parse `one {..} other {..}` option lists into a map. */
function parseOptions(style: string): Record<string, string> {
  const options: Record<string, string> = {};
  const pattern = /(\w+)\s*\{/g;
  let match: RegExpExecArray | null;

  while ((match = pattern.exec(style)) !== null) {
    const start = match.index + match[0].length;
    let depth = 1;
    let i = start;
    while (i < style.length && depth > 0) {
      if (style[i] === '{') depth++;
      else if (style[i] === '}') depth--;
      i++;
    }
    options[match[1]] = style.slice(start, i - 1);
  }

  return options;
}

/**
 * English plural rules — the mock only ever formats the `en` catalogue:
 * `one` for exactly 1, `other` for everything else.
 */
function pluralCategory(value: number): 'one' | 'other' {
  return value === 1 ? 'one' : 'other';
}

/**
 * A plain `{value}` argument is stringified as-is — `350000` stays `350000`,
 * without a thousands separator. That is what intl-messageformat does for a
 * value that is not wrapped in a number format.
 */
function formatValue(value: unknown): string {
  return String(value);
}

/**
 * The `#` placeholder inside a plural branch is a formatted number and does
 * carry the thousands separator: `350000` becomes `350,000`.
 */
function formatPluralNumber(value: unknown): string {
  if (typeof value === 'number') {
    return new Intl.NumberFormat('en').format(value);
  }
  return String(value);
}

/**
 * Format a message with the given params.
 *
 * Supports: `{name}`, `{name, plural, one {...} other {...}}`,
 * `{name, select, ...}` and the `#` placeholder inside a plural branch.
 */
export function formatMessage(message: string, params?: Record<string, unknown>): string {
  if (!params) return message;

  let output = '';
  for (const token of tokenize(message)) {
    if (!token.startsWith('{')) {
      output += token;
      continue;
    }

    const { name, type, style } = parseArgument(token);

    if (type === 'simple') {
      output += name in params ? formatValue(params[name]) : `{${name}}`;
      continue;
    }

    if (type === 'plural' || type === 'selectordinal') {
      const options = parseOptions(style);
      const raw = params[name];
      const category = pluralCategory(Number(raw));
      const branch = options[category] ?? options.other ?? '';
      output += formatMessage(branch, params).replace(/#/g, formatPluralNumber(raw));
      continue;
    }

    if (type === 'select') {
      const options = parseOptions(style);
      const raw = params[name];
      const branch = options[String(raw)] ?? options.other ?? '';
      output += formatMessage(branch, params);
      continue;
    }

    output += `{${name}}`;
  }

  return output;
}

const translatorCache = new Map<
  string,
  (key: string, params?: Record<string, unknown>) => string
>();

/**
 * A stable translator per namespace, the way next-intl hands it out. A fresh
 * function on every render would make every `useCallback` that depends on `t`
 * change identity, and a `useEffect` that depends on that callback would then
 * loop forever.
 */
const stableTranslator = (namespace?: string) => {
  const cacheKey = namespace ?? '';
  let cached = translatorCache.get(cacheKey);
  if (!cached) {
    cached = (key: string, params?: Record<string, unknown>) => {
      const value = resolve(namespace, key);
      // A key that does not exist in the catalogue must stay visible as the
      // key itself — that is how a missing translation shows up in a test.
      if (typeof value !== 'string') return key;
      return formatMessage(value, params);
    };
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
