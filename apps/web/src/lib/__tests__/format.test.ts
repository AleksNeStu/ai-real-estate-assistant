import { formatCompactPrice, formatPrice } from '../format';

/**
 * The Intl API puts a non-breaking space between a currency code and its
 * amount. The tests read the labels the way a screen reader reads them,
 * where that space is a space.
 */
const readable = (value: string): string => value.replace(/\u00a0/g, ' ');

describe('formatCompactPrice', () => {
  it('shortens an English price in dollars', () => {
    expect(formatCompactPrice(300000, 'USD', 'en')).toBe('$300K');
  });

  it('shortens an English price in zloty', () => {
    expect(readable(formatCompactPrice(300000, 'PLN', 'en'))).toBe('PLN 300K');
  });

  it('keeps one decimal when the number needs it', () => {
    expect(readable(formatCompactPrice(1250000, 'PLN', 'en'))).toBe('PLN 1.3M');
  });

  it('writes a Polish price the Polish way', () => {
    expect(readable(formatCompactPrice(300000, 'PLN', 'pl'))).toBe('300 tys. zł');
  });

  it('never pads a whole number with a zero', () => {
    // The currency style asks for two decimals by default. The compact
    // notation has no room for them, and the runtimes disagree about
    // whether to pad - "$300K" on one, "$300.0K" on another. The filters
    // of the map carried both spellings into the tests.
    expect(formatCompactPrice(300000, 'USD', 'en')).not.toContain('.0');
    expect(formatCompactPrice(300000, 'PLN', 'en')).not.toContain('.0');
  });

  it('returns an empty string for a missing price', () => {
    expect(formatCompactPrice(undefined)).toBe('');
    expect(formatCompactPrice(null)).toBe('');
  });
});

describe('formatPrice', () => {
  it('writes a full price in the currency of the listing', () => {
    expect(readable(formatPrice(620000, 'PLN', 'en'))).toBe('PLN 620,000');
  });

  it('survives an unknown currency', () => {
    expect(readable(formatPrice(1000, 'XXXX', 'en'))).toContain('1,000');
  });

  it('returns an empty string for a missing price', () => {
    expect(formatPrice(undefined)).toBe('');
  });
});
