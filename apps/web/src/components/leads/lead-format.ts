import type { LeadWithScore } from '@/lib/types';

/**
 * The two facts a lead card needs that are not on the lead itself.
 *
 * A lead is a person who searched, viewed or wrote. The API carries the
 * score, the contact details and the timestamps; what it does not carry is
 * the sentence a person wants to read on a card - "2-room, Nowa Huta, under
 * 500k". That sentence is assembled here from the parts the API does carry,
 * and nothing is added that the API did not say.
 */

/**
 * How long ago a moment was, in words.
 *
 * The reference point is passed in rather than read from the clock inside
 * the function, so the rendering stays pure and the test can pin it. When
 * the reference point is not known yet the plain date is stated instead.
 */
export function formatTimeAgo(
  dateString: string,
  locale: string,
  now: number | null
): string {
  const timestamp = new Date(dateString).getTime();
  if (Number.isNaN(timestamp)) return dateString;
  if (now === null) return new Date(timestamp).toLocaleDateString(locale);

  const formatter = new Intl.RelativeTimeFormat(locale, { numeric: 'auto' });
  const diffMinutes = Math.round((timestamp - now) / 60000);
  if (Math.abs(diffMinutes) < 60) return formatter.format(diffMinutes, 'minute');
  const diffHours = Math.round(diffMinutes / 60);
  if (Math.abs(diffHours) < 24) return formatter.format(diffHours, 'hour');
  const diffDays = Math.round(diffHours / 24);
  if (Math.abs(diffDays) < 30) return formatter.format(diffDays, 'day');
  return formatter.format(Math.round(diffDays / 30), 'month');
}

/**
 * The line under a lead's name: what the lead was looking for.
 *
 * The API carries the places the lead asked about, the budget it gave and
 * the source it came from. Whichever of those exist become the line; when
 * the lead carries none of them the line is empty rather than invented.
 */
export function leadInterestParts(
  lead: LeadWithScore
): { locations: string | null; budgetMax: number | null; source: string | null } {
  const locations = lead.preferred_locations?.length
    ? lead.preferred_locations.join(', ')
    : null;
  const budgetMax =
    typeof lead.budget_max === 'number' && Number.isFinite(lead.budget_max)
      ? lead.budget_max
      : null;
  const source = lead.source?.trim() ? lead.source.trim() : null;
  return { locations, budgetMax, source };
}

/**
 * The score at which a lead counts as high-value.
 *
 * The design says eighty; the API takes the threshold as a parameter, so
 * this is a setting of the board and not a fact about the market.
 */
export const HIGH_VALUE_THRESHOLD = 80;
