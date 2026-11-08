/**
 * The heatmap ramps.
 *
 * Mapbox parses the colours of a heatmap layer itself, so they cannot be CSS
 * variables — `var()` is not a colour the map engine understands. The ramps are
 * therefore literals, but they are the values of the design tokens
 * (`--chart-N`, `--success`, `--warning`, `--caution`, `--destructive`), and the
 * legend renders the very same constants, so the layer and the legend cannot
 * drift apart.
 */
import { PALETTE } from '@/lib/palette';
import type { HeatmapMode } from './property-map-utils';

const BLUE = PALETTE.chart1;
const TEAL = PALETTE.chart5;
const GREEN = PALETTE.success;
const AMBER = PALETTE.warning;
const ORANGE = PALETTE.caution;
const RED = PALETTE.destructive;

/** The visible stops of every ramp, low density to high density. */
export const HEATMAP_RAMPS: Record<HeatmapMode, string[]> = {
  density: [BLUE, TEAL, AMBER, ORANGE, RED],
  price: [GREEN, AMBER, ORANGE, RED],
  price_per_sqm: [GREEN, AMBER, ORANGE, RED],
  yield: [RED, ORANGE, AMBER, GREEN],
};

/**
 * The Mapbox expression for a ramp: the density starts fully transparent and
 * then walks the visible stops.
 */
export function heatmapColorExpression(mode: HeatmapMode): unknown[] {
  const ramp = HEATMAP_RAMPS[mode];
  const stops: unknown[] = ['interpolate', ['linear'], ['heatmap-density']];

  if (mode === 'density') {
    stops.push(0, transparentOf(ramp[0]));
    ramp.forEach((color, index) => {
      stops.push(0.2 + index * 0.2, color);
    });
    return stops;
  }

  stops.push(0, transparentOf(ramp[0]));
  const last = ramp.length - 1;
  ramp.forEach((color, index) => {
    stops.push(0.25 + (index / last) * 0.75, color);
  });
  return stops;
}

/** The same colour, fully transparent — the ramp starts out of sight. */
function transparentOf(color: string): string {
  return color.replace('hsl(', 'hsla(').replace(')', ', 0)');
}

/** The colours the legend paints, low to high. */
export function heatmapLegendColors(mode: HeatmapMode): string[] {
  return HEATMAP_RAMPS[mode];
}
