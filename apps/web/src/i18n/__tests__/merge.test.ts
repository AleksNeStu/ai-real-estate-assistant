import { describe, it, expect } from '@jest/globals';
import { mergeMessages, placeholderNames } from '../merge';

/**
 * The merge is what lets a catalogue stop moving. English decides the shape
 * and the placeholders; the locale decides the words it already has. These
 * tests pin both halves.
 */

const ENGLISH = {
  greeting: 'Hello {name}',
  nested: { title: 'The title', count: '{count} matches' },
  list: ['one', 'two'],
  rows: [{ cap: 'Capability', repo: 'In this repo' }],
};

describe('the message merge', () => {
  describe('placeholderNames', () => {
    it('names the arguments of a message', () => {
      expect(placeholderNames('a {count} b {amount} c')).toEqual(['amount', 'count']);
    });

    it('names the argument of a plural once', () => {
      expect(placeholderNames('{count, plural, one {x} other {y}}')).toEqual(['count']);
    });

    it('finds nothing in a message without arguments', () => {
      expect(placeholderNames('no arguments here')).toEqual([]);
    });
  });

  it('keeps the wording the locale already has', () => {
    const merged = mergeMessages(ENGLISH, {
      greeting: 'Cześć {name}',
      nested: { title: 'Tytuł', count: '{count} trafień' },
    });

    expect(merged.greeting).toBe('Cześć {name}');
    expect((merged.nested as Record<string, unknown>).title).toBe('Tytuł');
  });

  it('fills a key the locale does not carry from English', () => {
    const merged = mergeMessages(ENGLISH, { nested: { title: 'Tytuł' } });

    expect((merged.nested as Record<string, unknown>).count).toBe('{count} matches');
  });

  it('drops a key the locale invented', () => {
    const merged = mergeMessages(ENGLISH, { invented: 'Nic tu nie ma' });

    expect(Object.keys(merged)).toEqual(Object.keys(ENGLISH));
  });

  it('takes the English wording when the placeholders differ', () => {
    const merged = mergeMessages(ENGLISH, { greeting: 'Cześć {user}' });

    expect(merged.greeting).toBe('Hello {name}');
  });

  it('takes an array from the locale as a whole', () => {
    const merged = mergeMessages(ENGLISH, { list: ['jedno', 'dwa'] });

    expect(merged.list).toEqual(['jedno', 'dwa']);
  });

  it('takes the English array when the locale lost it', () => {
    const merged = mergeMessages(ENGLISH, { list: [] });

    expect(merged.list).toEqual(['one', 'two']);
  });

  it('takes the English value when the shape does not match', () => {
    const merged = mergeMessages(ENGLISH, { nested: 'a string where an object belongs' });

    expect(merged.nested).toEqual(ENGLISH.nested);
  });
});
