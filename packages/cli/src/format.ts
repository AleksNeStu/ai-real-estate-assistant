/**
 * How an answer is printed.
 *
 * A command that prints JSON is a command whose output has to be read by a
 * machine; a command that prints a ledger is a command whose output has to be
 * read by a person. Both are offered, and the default is the one a person
 * asked for.
 */

/** A number as a person reads it: grouped, without a fraction. */
export function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return '-';
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(value);
}

/** A price with its currency. */
export function formatMoney(
  value: number | null | undefined,
  currency: string | null | undefined,
): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return '-';
  const code = currency && currency.trim() ? currency.trim().toUpperCase() : 'PLN';
  return `${formatNumber(value)} ${code}`;
}

/** A line of `label: value`, with the label in a fixed width so the values line up. */
export function field(label: string, value: string): string {
  return `${label.padEnd(22, ' ')}${value}`;
}
