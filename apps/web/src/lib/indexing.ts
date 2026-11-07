/**
 * The indexing guard.
 *
 * A deployment that is not ready to be published - an internal demo, a review
 * build - must not be indexed. An indexed half-finished page is far harder to
 * un-index than it is to keep out of the index, and the product here is still
 * in that state.
 *
 * `SEARCH_INDEXING` is read from the RUNTIME environment, so one image serves
 * an indexable deployment and a private one without a rebuild. Unset means
 * "indexable" - the public repository keeps the SEO surface it ships.
 */

export const ROBOTS_TAG_HEADER = 'X-Robots-Tag';

export function isIndexingEnabled(): boolean {
  return process.env.SEARCH_INDEXING !== 'false';
}

/**
 * Mark the response as not indexable when the deployment asked for it.
 *
 * The header is set on every page the proxy serves, so a crawler that reaches
 * a page by a direct link (a share, a chat message) still learns that the
 * page must not go into an index.
 */
export function applyIndexingGuard(headers: { set(name: string, value: string): void }): void {
  if (!isIndexingEnabled()) {
    headers.set(ROBOTS_TAG_HEADER, 'noindex, nofollow');
  }
}
