import { describe, it, expect } from '@jest/globals';
import { isMaintained, maintainedLocales } from '../policy';

/**
 * The interface ships in nine languages and is maintained in three of them.
 * The lists themselves are asserted where they are named, in `config.test.ts`;
 * this file holds the question a rule or a test asks.
 */

describe('the language policy', () => {
  it('knows which locale is maintained', () => {
    expect(isMaintained('en')).toBe(true);
    expect(isMaintained('pl')).toBe(true);
    expect(isMaintained('ru')).toBe(true);
    expect(isMaintained('fr')).toBe(false);
  });

  it('names English, Polish and Russian', () => {
    expect([...maintainedLocales].sort()).toEqual(['en', 'pl', 'ru']);
  });
});
