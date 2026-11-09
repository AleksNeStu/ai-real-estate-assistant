import { describe, it, expect } from '@jest/globals';
import { locales } from '../config';
import { frozenLocales, isMaintained, maintainedLocales } from '../policy';

/**
 * The interface ships in nine languages and is maintained in two of them.
 * These tests hold that split in place.
 */

describe('the language policy', () => {
  it('maintains English and Polish', () => {
    expect([...maintainedLocales].sort()).toEqual(['en', 'pl']);
  });

  it('freezes the other seven', () => {
    expect([...frozenLocales].sort()).toEqual(['de', 'es', 'it', 'pt', 'ru', 'tr', 'uk']);
  });

  it('covers every locale exactly once', () => {
    expect([...maintainedLocales, ...frozenLocales].sort()).toEqual([...locales].sort());
  });

  it('knows which locale is maintained', () => {
    expect(isMaintained('en')).toBe(true);
    expect(isMaintained('pl')).toBe(true);
    expect(isMaintained('ru')).toBe(false);
    expect(isMaintained('fr')).toBe(false);
  });
});
