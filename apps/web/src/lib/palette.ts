/**
 * The colours that cannot be read from CSS.
 *
 * The design tokens live in `app/globals.css` as raw HSL channels, and the
 * Tailwind utilities read them through the `@theme inline` aliases. One
 * consumer cannot go that way: the map engines (Mapbox and Leaflet parse
 * their own colour strings and do not understand `var()`).
 *
 * This file is the single place where those literals live. Each one is the
 * value of a named token, and `lib/__tests__/palette-tokens.test.ts` asserts
 * that equality against `globals.css` - so a token that moves and a literal
 * that does not is a failing test, not a visual bug nobody notices.
 */

const hsl = (h: number, s: number, l: number) => `hsl(${h}, ${s}%, ${l}%)`;

/** The status ramp, as the tokens define it. */
export const PALETTE = {
  /** --chart-1 */
  chart1: hsl(221, 83, 53),
  /** --chart-5 */
  chart5: hsl(192, 91, 39),
  /** --success */
  success: hsl(142, 71, 28),
  /** --warning */
  warning: hsl(26, 90, 37),
  /** --caution */
  caution: hsl(20, 90, 38),
  /** --destructive */
  destructive: hsl(0, 72.2, 43.5),
  /** --action - the teal of the single primary action (#0f766e) */
  action: hsl(175.34, 77.44, 26.08),
} as const;

/**
 * The action colour as a hex.
 *
 * Most of the app reads the teal from the token. The browser chrome cannot:
 * `themeColor` is a static export and takes a literal colour, so it is
 * written out here and the parity test asserts it against `--action`.
 */
export const ACTION_HEX = '#0f766e';

/**
 * The token each literal stands for. The parity test walks this table and
 * compares the literal with the token in `globals.css`.
 */
export const TOKEN_SOURCES: Record<string, string> = {
  [PALETTE.chart1]: '--chart-1',
  [PALETTE.chart5]: '--chart-5',
  [PALETTE.success]: '--success',
  [PALETTE.warning]: '--warning',
  [PALETTE.caution]: '--caution',
  [PALETTE.destructive]: '--destructive',
  [PALETTE.action]: '--action',
};
