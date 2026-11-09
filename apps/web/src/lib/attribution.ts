/**
 * Attribution: where the visitor came from inside the site, and where they
 * went next.
 *
 * A same-site link carries `?from=<slot>` (see `lib/utm.ts`). On arrival the
 * slot is reported as a navigation interaction, so the funnel can answer
 * "which line of the landing brought the visitor in" - and the parameter is
 * removed, so a reload does not count the same arrival twice.
 *
 * An outbound link cannot be measured server-side: the browser leaves the
 * site before the request could be counted. The click is therefore reported
 * from the browser, before the navigation happens.
 */
import { buildHeaders, getApiUrl } from '@/lib/api/client';

const SLOT_PARAM = 'from';

/** The slot of the current arrival, if any. */
export function currentSlot(): string | null {
  if (typeof window === 'undefined') return null;
  const slot = new URLSearchParams(window.location.search).get(SLOT_PARAM);
  return slot && slot.trim() ? slot.trim() : null;
}

/**
 * Report the arrival slot and drop the parameter from the address bar.
 * Never throws: a broken measurement must not break the page.
 */
export async function reportArrival(): Promise<void> {
  const slot = currentSlot();
  if (!slot) return;

  try {
    await fetch(`${getApiUrl()}/leads/track`, {
      method: 'POST',
      headers: buildHeaders(),
      body: JSON.stringify({
        interaction_type: 'navigation',
        metadata: { slot },
        page_url: window.location.pathname,
      }),
      keepalive: true,
    });
  } catch {
    // The measurement is best effort.
  }

  try {
    const url = new URL(window.location.href);
    url.searchParams.delete(SLOT_PARAM);
    window.history.replaceState({}, '', url.toString());
  } catch {
    // A browser that refuses the history API keeps the parameter.
  }
}

/**
 * Report an outbound click. Call it from the click handler of the link, so
 * the request starts before the browser leaves the page.
 */
export async function reportOutbound(
  target: string,
  slot: string,
  campaign?: string
): Promise<void> {
  try {
    await fetch(`${getApiUrl()}/analytics/outbound`, {
      method: 'POST',
      headers: buildHeaders(),
      body: JSON.stringify({ target, slot, campaign: campaign ?? null }),
      keepalive: true,
    });
  } catch {
    // The measurement is best effort.
  }
}
