import { type PropertyMapPoint } from "./property-map-utils";

export type ClusteredMapItem =
  | { kind: "point"; point: PropertyMapPoint }
  | {
      kind: "cluster";
      id: string;
      lat: number;
      lon: number;
      count: number;
      points: PropertyMapPoint[];
      dominantType: string | null;
      typeDistribution: Map<string, number>;
      isMixed: boolean;
    };

export type ClusterOptions = {
  cellSizePx?: number;
  maxPointsWithoutClustering?: number;
  maxZoomForClustering?: number;
};

/**
 * The colour of every property type.
 *
 * The palette lives in the design tokens, so a marker follows the theme
 * instead of pinning a hex value that only reads well in the light theme.
 */
export const PROPERTY_TYPE_COLORS: Record<string, string> = {
  apartment: "hsl(var(--chart-1))",
  house: "hsl(var(--chart-2))",
  studio: "hsl(var(--chart-4))",
  loft: "hsl(var(--caution))",
  townhouse: "hsl(var(--chart-5))",
  other: "hsl(var(--muted-foreground))",
};

/**
 * Get cluster color based on dominant property type.
 * @param dominantType - The dominant property type in the cluster
 * @param isMixed - Whether the cluster contains multiple property types
 * @returns CSS color string
 */
export function getClusterColor(
  dominantType: string | null,
  isMixed: boolean
): string {
  // Mixed clusters get a neutral color
  if (isMixed) {
    return "hsl(var(--muted-foreground))";
  }
  // Use the color for the dominant type, fallback to gray
  return PROPERTY_TYPE_COLORS[dominantType ?? "other"] ?? PROPERTY_TYPE_COLORS.other;
}

export interface ClusterTypeAnalysis {
  dominantType: string | null;
  distribution: Map<string, number>;
  isMixed: boolean;
}

export function analyzeClusterTypes(points: PropertyMapPoint[]): ClusterTypeAnalysis {
  const typeCounts = new Map<string, number>();
  let totalTyped = 0;

  for (const point of points) {
    const type = point.property_type || "other";
    typeCounts.set(type, (typeCounts.get(type) || 0) + 1);
    totalTyped++;
  }

  // Calculate distribution percentages
  const distribution = new Map<string, number>();
  for (const [type, count] of typeCounts) {
    distribution.set(type, (count / totalTyped) * 100);
  }

  // Find dominant type (>50%)
  let dominantType: string | null = null;
  let maxPercentage = 0;
  for (const [type, percentage] of distribution) {
    if (percentage > 50 && percentage > maxPercentage) {
      dominantType = type;
      maxPercentage = percentage;
    }
  }

  const isMixed = dominantType === null && typeCounts.size > 1;

  return { dominantType, distribution, isMixed };
}

const TILE_SIZE_PX = 256;

function toRad(value: number): number {
  return (value * Math.PI) / 180;
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function latLonToWorldPx(
  lat: number,
  lon: number,
  zoom: number
): {
  x: number;
  y: number;
} {
  const scale = TILE_SIZE_PX * Math.pow(2, zoom);
  const x = ((lon + 180) / 360) * scale;
  const sinLat = Math.sin(toRad(clamp(lat, -85.05112878, 85.05112878)));
  const y = (0.5 - Math.log((1 + sinLat) / (1 - sinLat)) / (4 * Math.PI)) * scale;
  return { x, y };
}

export function clusterMapPoints(points: PropertyMapPoint[], zoom: number, options: ClusterOptions = {}): ClusteredMapItem[] {
  let cellSizePx = options.cellSizePx ?? 60;
  const maxPointsWithoutClustering = options.maxPointsWithoutClustering ?? 75;
  const maxZoomForClustering = options.maxZoomForClustering ?? 15;

  if (points.length <= maxPointsWithoutClustering || zoom >= maxZoomForClustering) {
    return points.map((point) => ({ kind: "point", point }));
  }

  // Dynamic cell size adjustment for very dense areas (1000+ points)
  if (points.length > 1000) {
    // Increase cell size by up to 50% for very dense datasets
    const densityFactor = Math.min(points.length / 1000, 2);
    cellSizePx = Math.round(cellSizePx * (1 + densityFactor * 0.25));
  }

  const groups = new Map<
    string,
    {
      cellX: number;
      cellY: number;
      points: PropertyMapPoint[];
      sumLat: number;
      sumLon: number;
    }
  >();

  for (const point of points) {
    const { x, y } = latLonToWorldPx(point.lat, point.lon, zoom);
    const cellX = Math.floor(x / cellSizePx);
    const cellY = Math.floor(y / cellSizePx);
    const key = `${cellX}:${cellY}`;

    const existing = groups.get(key);
    if (!existing) {
      groups.set(key, { cellX, cellY, points: [point], sumLat: point.lat, sumLon: point.lon });
      continue;
    }

    existing.points.push(point);
    existing.sumLat += point.lat;
    existing.sumLon += point.lon;
  }

  return Array.from(groups.values())
    .sort((a, b) => {
      if (a.cellY !== b.cellY) return a.cellY - b.cellY;
      return a.cellX - b.cellX;
    })
    .reduce<ClusteredMapItem[]>((acc, group) => {
      if (group.points.length === 1) {
        acc.push({ kind: "point", point: group.points[0] });
        return acc;
      }

      const count = group.points.length;
      const lat = group.sumLat / count;
      const lon = group.sumLon / count;

      // Analyze property types in cluster
      const typeAnalysis = analyzeClusterTypes(group.points);

      acc.push({
        kind: "cluster",
        id: `cluster-${group.cellX}-${group.cellY}`,
        lat,
        lon,
        count,
        points: group.points,
        dominantType: typeAnalysis.dominantType,
        typeDistribution: typeAnalysis.distribution,
        isMixed: typeAnalysis.isMixed,
      });
      return acc;
    }, []);
}
