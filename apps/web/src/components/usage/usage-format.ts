/**
 * The usage route's two small formatters.
 *
 * The usage page states dates and periods in mono, and the way it states
 * them must not depend on the machine it is rendered on - so the format is
 * explicit rather than the default of the runtime.
 */

/** The five kinds of event the API counts. */
export type UsageEventKind = 'search' | 'view' | 'click' | 'tool_call' | 'download';

/** The kinds of event, in the order the tiles carry them. */
export const USAGE_EVENT_KINDS: UsageEventKind[] = [
  'search',
  'view',
  'click',
  'tool_call',
  'download',
];

/**
 * A day, as the design states it: the day and the month, no year.
 *
 * The year is left out on purpose - a usage window is always inside one
 * year, and the shorter the label the narrower the axis stays.
 */
export function formatDay(date: string, locale: string): string {
  const parsed = new Date(date);
  if (Number.isNaN(parsed.getTime())) return date;
  return new Intl.DateTimeFormat(locale, { day: 'numeric', month: 'short' }).format(parsed);
}

/**
 * A period, as the design states it: two days, one at each end.
 */
export function formatPeriod(start: string, end: string, locale: string): string {
  return `${formatDay(start, locale)} – ${formatDay(end, locale)}`;
}

/**
 * The number of events in a period, counted from the tiles.
 */
export function totalEvents(totals: Record<UsageEventKind, number>): number {
  return USAGE_EVENT_KINDS.reduce((sum, kind) => sum + (totals[kind] ?? 0), 0);
}
