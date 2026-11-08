import type { PropertyMapPoint } from "@/components/search/property-map-utils";

export interface DistrictStats {
  name: string;
  count: number;
  avgPrice: number | null;
  minPrice: number | null;
  maxPrice: number | null;
  avgPricePerSqm: number | null;
  center: [number, number]; // [lon, lat]
  bounds: [[number, number], [number, number]]; // [[minLon, minLat], [maxLon, maxLat]]
}

export interface DistrictBoundary {
  id: string;
  name: string;
  center: [number, number];
  bounds: [[number, number], [number, number]];
  polygon: [number, number][]; // [lon, lat] pairs
}

/**
 * Calculate statistics for properties within district boundaries
 */
export function aggregateByDistrict(
  points: PropertyMapPoint[],
  boundaries: DistrictBoundary[]
): DistrictStats[] {
  const stats: Map<string, DistrictStats> = new Map();

  // Initialize stats for each district
  boundaries.forEach((boundary) => {
    stats.set(boundary.id, {
      name: boundary.name,
      count: 0,
      avgPrice: null,
      minPrice: null,
      maxPrice: null,
      avgPricePerSqm: null,
      center: boundary.center,
      bounds: boundary.bounds,
    });
  });

  // Assign points to districts
  points.forEach((point) => {
    const boundary = boundaries.find((b) =>
      pointInPolygon(point.lat, point.lon, b.polygon)
    );

    if (boundary) {
      const district = stats.get(boundary.id)!;
      district.count++;
    }
  });

  // Calculate price stats for each district
  const districtPoints: Map<string, PropertyMapPoint[]> = new Map();
  boundaries.forEach((b) => districtPoints.set(b.id, []));

  points.forEach((point) => {
    const boundary = boundaries.find((b) =>
      pointInPolygon(point.lat, point.lon, b.polygon)
    );
    if (boundary) {
      districtPoints.get(boundary.id)!.push(point);
    }
  });

  districtPoints.forEach((pts, id) => {
    const district = stats.get(id);
    if (!district || pts.length === 0) return;

    const prices = pts
      .map((p) => p.price)
      .filter((p): p is number => p !== undefined);

    const pricesPerSqm = pts
      .map((p) => p.price_per_sqm)
      .filter((p): p is number => p !== undefined);

    if (prices.length > 0) {
      district.avgPrice = Math.round(prices.reduce((a, b) => a + b, 0) / prices.length);
      district.minPrice = Math.min(...prices);
      district.maxPrice = Math.max(...prices);
    }

    if (pricesPerSqm.length > 0) {
      district.avgPricePerSqm = Math.round(
        pricesPerSqm.reduce((a, b) => a + b, 0) / pricesPerSqm.length
      );
    }
  });

  return Array.from(stats.values()).filter((s) => s.count > 0);
}

/**
 * Check if a point is inside a polygon using ray casting algorithm
 */
export function pointInPolygon(
  lat: number,
  lon: number,
  polygon: [number, number][]
): boolean {
  if (polygon.length < 3) return false;

  let inside = false;
  const n = polygon.length;

  for (let i = 0, j = n - 1; i < n; j = i++) {
    const xi = polygon[i][0]; // lon
    const yi = polygon[i][1]; // lat
    const xj = polygon[j][0];
    const yj = polygon[j][1];

    if (((yi > lat) !== (yj > lat)) && (lon < ((xj - xi) * (lat - yi)) / (yj - yi) + xi)) {
      inside = !inside;
    }
  }

  return inside;
}

/**
 * Get color for district based on average price (choropleth)
 */
export function getDistrictColor(avgPrice: number | null, maxPrice: number): string {
  // Mapbox paints this layer itself and does not understand CSS variables,
  // so the colours are the values of the design tokens in a literal form.
  if (avgPrice === null) return "hsla(240, 4%, 46%, 0.3)"; // Muted - no data

  const ratio = avgPrice / maxPrice;

  if (ratio < 0.25) return "hsla(142, 76%, 36%, 0.4)"; // Success - low
  if (ratio < 0.5) return "hsla(32, 95%, 44%, 0.4)"; // Warning - medium-low
  if (ratio < 0.75) return "hsla(20, 90%, 48%, 0.4)"; // Caution - medium-high
  return "hsla(0, 84%, 60%, 0.4)"; // Destructive - high
}

/**
 * Sample district boundaries for Warsaw
 * In production, this would be loaded from GeoJSON files or API
 */
export const WARSAW_DISTRICTS: DistrictBoundary[] = [
  {
    id: "warsaw-srodmiescie",
    name: "Śródmieście",
    center: [21.0122, 52.2297],
    bounds: [[21.0, 52.22], [21.03, 52.24]],
    polygon: [
      [21.0, 52.22],
      [21.03, 52.22],
      [21.03, 52.24],
      [21.0, 52.24],
      [21.0, 52.22],
    ],
  },
  {
    id: "warsaw-mokotow",
    name: "Mokotów",
    center: [21.0, 52.19],
    bounds: [[20.97, 52.17], [21.05, 52.21]],
    polygon: [
      [20.97, 52.17],
      [21.05, 52.17],
      [21.05, 52.21],
      [20.97, 52.21],
      [20.97, 52.17],
    ],
  },
  {
    id: "warsaw-zoliborz",
    name: "Żoliborz",
    center: [20.99, 52.26],
    bounds: [[20.97, 52.25], [21.02, 52.28]],
    polygon: [
      [20.97, 52.25],
      [21.02, 52.25],
      [21.02, 52.28],
      [20.97, 52.28],
      [20.97, 52.25],
    ],
  },
  {
    id: "warsaw-ursynow",
    name: "Ursynów",
    center: [21.05, 52.15],
    bounds: [[21.0, 52.13], [21.12, 52.18]],
    polygon: [
      [21.0, 52.13],
      [21.12, 52.13],
      [21.12, 52.18],
      [21.0, 52.18],
      [21.0, 52.13],
    ],
  },
  {
    id: "warsaw-wola",
    name: "Wola",
    center: [20.97, 52.235],
    bounds: [[20.94, 52.22], [21.0, 52.25]],
    polygon: [
      [20.94, 52.22],
      [21.0, 52.22],
      [21.0, 52.25],
      [20.94, 52.25],
      [20.94, 52.22],
    ],
  },
];

/**
 * Load district boundaries for a city
 * In production, this would fetch from API or load from GeoJSON files
 */
export async function loadDistrictBoundaries(city: string): Promise<DistrictBoundary[]> {
  // For now, return sample data for Warsaw
  const cityLower = city.toLowerCase();

  if (cityLower === "warsaw" || cityLower === "warszawa") {
    return WARSAW_DISTRICTS;
  }

  // For other cities, return empty array
  // In production, you would:
  // 1. Fetch from Overpass API
  // 2. Load from local GeoJSON files
  // 3. Use a district boundaries API
  return [];
}
