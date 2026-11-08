/**
 * The next-intl mock formats ICU messages itself (plurals, placeholders) so
 * that tests assert the copy a user actually sees. This test pins that
 * formatter to the real next-intl behaviour.
 *
 * `intl-messageformat` is the package next-intl formats with. It reaches the
 * app as a transitive dependency, so the comparison is optional: when the
 * package is not resolvable the reference expectations still hold.
 */
import { formatMessage } from '../next-intl';

type MessageFormatter = (
  message: string,
  locale: string
) => (params: Record<string, unknown>) => string;

let reference: MessageFormatter | null = null;
try {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { IntlMessageFormat } = require('intl-messageformat');
  reference = (message: string, locale: string) => (params: Record<string, unknown>) =>
    new IntlMessageFormat(message, locale).format(params);
} catch {
  reference = null;
}

const ICU_MESSAGES = [
  '{count, plural, one {# saved property} other {# saved properties}}',
  'Showing {count} {count, plural, one {property} other {properties}}',
  '{count, plural, one {# bed} other {# beds}}',
  '{count, plural, one {# nieruchomość} few {# nieruchomości} other {# nieruchomości}}',
  '{count, plural, one {# property} other {# properties}} across {cities, plural, one {# city} other {# cities}}',
  '{cities, plural, one {# şehirde} other {# şehirde}} {count, plural, one {# mülk} other {# mülk}}',
  'Score: {score}',
  'Comparables ({count})',
  'Variable {name}',
];

const EXPECTED: Record<string, Record<string, string>> = {
  '{count, plural, one {# saved property} other {# saved properties}}': {
    '0': '0 saved properties',
    '1': '1 saved property',
    '2': '2 saved properties',
    '5': '5 saved properties',
    // The `#` placeholder inside a plural branch is a formatted number and
    // therefore carries the thousands separator, unlike a plain `{count}`.
    '350000': '350,000 saved properties',
  },
  'Showing {count} {count, plural, one {property} other {properties}}': {
    '1': 'Showing 1 property',
    '2': 'Showing 2 properties',
    '350000': 'Showing 350000 properties',
  },
  '{count, plural, one {# bed} other {# beds}}': {
    '1': '1 bed',
    '3': '3 beds',
  },
  'Score: {score}': { '1': 'Score: 1', '350000': 'Score: 350000' },
  'Comparables ({count})': { '2': 'Comparables (2)', '350000': 'Comparables (350000)' },
  'Variable {name}': { '1': 'Variable 1' },
};

describe('mock ICU formatter', () => {
  it.each(ICU_MESSAGES)('renders %s', (message) => {
    const names = [...message.matchAll(/\{(\w+)\s*[,}]/g)].map((m) => m[1]);
    for (const count of [0, 1, 2, 5]) {
      const params: Record<string, unknown> = {};
      for (const name of names) {
        params[name] = name === 'count' || name === 'cities' ? count : 'X';
      }
      const rendered = formatMessage(message, params);
      expect(typeof rendered).toBe('string');
      expect(rendered).not.toContain('{count');
    }
  });

  it.each(Object.entries(EXPECTED))('renders %s with the expected copy', (message, expected) => {
    for (const [count, copy] of Object.entries(expected)) {
      const names = [...message.matchAll(/\{(\w+)\s*[,}]/g)].map((m) => m[1]);
      const params: Record<string, unknown> = {};
      for (const name of names) {
        params[name] = Number(count);
      }
      expect(formatMessage(message, params)).toBe(copy);
    }
  });

  const withReference = reference ? it.each : it.each.skip;
  withReference(ICU_MESSAGES)('matches intl-messageformat for %s', (message) => {
    const format = reference!(message, 'en');
    const names = [...message.matchAll(/\{(\w+)\s*[,}]/g)].map((m) => m[1]);
    // 350000 is included on purpose: it separates the two number formats —
    // a plain `{value}` stays ungrouped, the `#` inside a plural is grouped.
    for (const count of [0, 1, 2, 5, 350000]) {
      const params: Record<string, unknown> = {};
      for (const name of names) {
        params[name] = name === 'count' || name === 'cities' ? count : 'X';
      }
      expect(formatMessage(message, params)).toBe(format(params));
    }
  });

  it('keeps an unknown placeholder visible', () => {
    expect(formatMessage('Hello {name}', {})).toBe('Hello {name}');
  });

  it('returns the message unchanged without params', () => {
    expect(formatMessage('Hello {name}')).toBe('Hello {name}');
  });
});
