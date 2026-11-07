/**
 * The indexing guard.
 *
 * A deployment that is not ready to be published must be able to say so at
 * RUNTIME, without a rebuild: `SEARCH_INDEXING=false` marks every response as
 * `noindex, nofollow`. Unset - the default, and what the public repository
 * ships - leaves the indexable surface untouched.
 */

import { applyIndexingGuard, isIndexingEnabled, ROBOTS_TAG_HEADER } from '@/lib/indexing';

const ORIGINAL_ENV = process.env.SEARCH_INDEXING;

function fakeHeaders(): { set: jest.Mock; get: (name: string) => string | undefined } {
  const store = new Map<string, string>();
  return {
    set: jest.fn((name: string, value: string) => {
      store.set(name, value);
    }),
    get: (name: string) => store.get(name),
  };
}

describe('the indexing guard', () => {
  afterEach(() => {
    if (ORIGINAL_ENV === undefined) {
      delete process.env.SEARCH_INDEXING;
    } else {
      process.env.SEARCH_INDEXING = ORIGINAL_ENV;
    }
  });

  it('treats an unset flag as indexable', () => {
    delete process.env.SEARCH_INDEXING;

    expect(isIndexingEnabled()).toBe(true);
  });

  it('treats an explicit "true" as indexable', () => {
    process.env.SEARCH_INDEXING = 'true';

    expect(isIndexingEnabled()).toBe(true);
  });

  it('treats "false" as not indexable', () => {
    process.env.SEARCH_INDEXING = 'false';

    expect(isIndexingEnabled()).toBe(false);
  });

  it('leaves the response alone when indexing is enabled', () => {
    delete process.env.SEARCH_INDEXING;
    const headers = fakeHeaders();

    applyIndexingGuard(headers);

    expect(headers.set).not.toHaveBeenCalled();
    expect(headers.get(ROBOTS_TAG_HEADER)).toBeUndefined();
  });

  it('marks the response as not indexable when indexing is switched off', () => {
    process.env.SEARCH_INDEXING = 'false';
    const headers = fakeHeaders();

    applyIndexingGuard(headers);

    expect(headers.get(ROBOTS_TAG_HEADER)).toBe('noindex, nofollow');
  });
});
