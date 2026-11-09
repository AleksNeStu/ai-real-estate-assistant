/**
 * The colours that cannot be read from CSS.
 *
 * The design tokens live in `app/globals.css` as raw HSL channels, and the
 * Tailwind utilities read them through the `@theme inline` aliases. Two
 * consumers cannot go that way: the map engines (Mapbox and Leaflet parse
 * their own colour strings and do not understand `var()`), and the GeoJSON
 * style objects that Mapbox paints itself.
 *
 * This file is the single place where those literals live. Each one is the
 * value of a named token, and `lib/__tests__/palette-tokens.test.ts` asserts
 * that equality against `globals.css` - so a token that moves and a literal
 * that does not is a failing test, not a visual bug nobody notices.
 */

const hsl = (h: number, s: number, l: number) => `hsl(${h}, ${s}%, ${l}%)`;
const hsla = (h: number, s: number, l: number, a: number) =>
  `hsla(${h}, ${s}%, ${l}%, ${a})`;

/** The status ramp, as the tokens define it. */
export const PALETTE = {
  /** --chart-1 */
  chart1: hsl(221, 83, 53),
  /** --chart-5 */
  chart5: hsl(192, 91, 39),
  /** --success */
  success: hsl(142, 76, 36),
  /** --warning */
  warning: hsl(26, 90, 37),
  /** --caution */
  caution: hsl(20, 90, 48),
  /** --destructive */
  destructive: hsl(0, 84.2, 60.2),
  /** --action - the teal of the single primary action (#0f766e) */
  action: hsl(175.34, 77.44, 26.08),
  /** --muted-foreground, the muted grey of a choropleth without data */
  muted: hsl(240, 3.8, 46.1),
} as const;

/**
 * The choropleth fill of a district, by the share of the maximum price.
 * The four bands are the success, warning, caution and destructive tokens at
 * 40% opacity, and the "no data" band the muted foreground at 30%.
 */
export const DISTRICT_FILL = {
  noData: hsla(240, 3.8, 46.1, 0.3),
  low: hsla(142, 76, 36, 0.4),
  mediumLow: hsla(26, 90, 37, 0.4),
  mediumHigh: hsla(20, 90, 48, 0.4),
  high: hsla(0, 84.2, 60.2, 0.4),
} as const;

/** The Mapbox style colours of the district boundary layer. */
export const DISTRICT_LAYER = {
  /** --district-line */
  line: hsl(217, 19, 26.7),
  /** --district-label */
  label: hsl(215, 27.9, 16.9),
  /** --district-halo */
  halo: hsl(0, 0, 100),
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
  [PALETTE.muted]: '--muted-foreground',
  [DISTRICT_LAYER.line]: '--district-line',
  [DISTRICT_LAYER.label]: '--district-label',
  [DISTRICT_LAYER.halo]: '--district-halo',
};
