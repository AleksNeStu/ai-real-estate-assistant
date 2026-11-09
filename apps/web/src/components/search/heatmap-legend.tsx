"use client";

import { heatmapLegendColors } from "./heatmap-colors";
import type { HeatmapMode } from "./property-map-utils";
import { formatCompactPrice } from "@/lib/format";

interface HeatmapLegendProps {
  mode: HeatmapMode;
  minValue?: number;
  maxValue?: number;
  /** The currency the listings on the map are priced in. */
  currency?: string;
  locale?: string;
  className?: string;
}

const MODE_CONFIG: Record<HeatmapMode, { label: string; unit: string }> = {
  density: {
    label: "Property Density",
    unit: "",
  },
  price: {
    label: "Price",
    unit: "",
  },
  price_per_sqm: {
    label: "Price per m²",
    unit: "/m²",
  },
  yield: {
    label: "Rental Yield",
    unit: "%",
  },
};
function formatValue(
  value: number | undefined,
  mode: HeatmapMode,
  currency: string,
  locale: string
): string {
  if (value === undefined) return "-";

  if (mode === "density") return "";
  if (mode === "yield") return `${value.toFixed(1)}%`;

  // Price and price_per_sqm, in the currency of the listings themselves -
  // the legend used to spell a dollar sign into every price.
  return formatCompactPrice(value, currency, locale);
}

export default function HeatmapLegend({
  mode,
  minValue,
  maxValue,
  currency = "PLN",
  locale = "pl-PL",
  className = "",
}: HeatmapLegendProps) {
  const config = MODE_CONFIG[mode];
  // The legend paints the very same constants the map layer uses.
  const gradientColors = heatmapLegendColors(mode).join(", ");

  return (
    <div
      className={`bg-background/95 backdrop-blur-sm rounded-lg border shadow-sm p-2 ${className}`}
      role="figure"
      aria-label={`${config.label} legend`}
    >
      <div className="text-xs font-medium text-muted-foreground mb-1">
        {config.label}
      </div>
      <div
        className="h-3 rounded-sm"
        style={{
          background: `linear-gradient(to right, ${gradientColors})`,
        }}
      />
      <div className="flex justify-between mt-1">
        <span className="text-xs text-muted-foreground">
          {formatValue(minValue, mode, currency, locale)}
        </span>
        <span className="text-xs text-muted-foreground">
          {formatValue(maxValue, mode, currency, locale)}
        </span>
      </div>
    </div>
  );
}
