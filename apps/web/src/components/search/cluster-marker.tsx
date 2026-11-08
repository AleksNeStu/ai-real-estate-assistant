'use client';

import { PROPERTY_TYPE_COLORS } from './property-map-clustering';

interface ClusterMarkerProps {
  count: number;
  dominantType: string | null;
  typeDistribution: Map<string, number>;
  isMixed: boolean;
}

/**
 * Get the color for a cluster based on dominant property type
 */
export function getClusterColor(dominantType: string | null, isMixed: boolean): string {
  if (isMixed) {
    return 'hsl(var(--muted-foreground))';
  }
  return PROPERTY_TYPE_COLORS[dominantType || 'other'] || PROPERTY_TYPE_COLORS.other;
}

/**
 * Segment data for the mixed-type bar
 */
interface BarSegment {
  width: number;
  color: string;
}

/**
 * Compute segments for the mixed-type distribution bar.
 * Returns sorted segments (top 3 types + gray fill) with percentage widths.
 */
export function computeBarSegments(distribution: Map<string, number>): BarSegment[] {
  const sortedTypes = Array.from(distribution.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3);

  const segments: BarSegment[] = [];
  let accumulatedWidth = 0;

  for (const [type, percentage] of sortedTypes) {
    const width = Math.round((percentage / 100) * 100);
    const color = PROPERTY_TYPE_COLORS[type] || PROPERTY_TYPE_COLORS.other;
    segments.push({ width, color });
    accumulatedWidth += width;
  }

  if (accumulatedWidth < 100) {
    segments.push({ width: 100 - accumulatedWidth, color: 'hsl(var(--muted-foreground))' });
  }

  return segments;
}

/**
 * ClusterMarker - Renders a styled cluster marker
 */
export default function ClusterMarker({
  count,
  dominantType,
  typeDistribution,
  isMixed,
}: ClusterMarkerProps) {
  const backgroundColor = getClusterColor(dominantType, isMixed);
  const displayCount = count >= 1000 ? `${Math.floor(count / 1000)}K+` : count.toString();

  const segments = isMixed && typeDistribution.size > 1 ? computeBarSegments(typeDistribution) : [];

  return (
    <div
      className="mapbox-marker-cluster"
      role="img"
      aria-label={`${count} properties clustered`}
      style={{
        minWidth: count >= 100 ? '40px' : count >= 50 ? '35px' : '30px',
        height: count >= 100 ? '40px' : count >= 50 ? '35px' : '30px',
        padding: '0 8px',
        background: backgroundColor,
        color: 'hsl(var(--background))',
        borderRadius: '9999px',
        border: '2px solid hsl(var(--background))',
        boxShadow: '0 2px 4px hsl(var(--foreground) / 0.3)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        fontWeight: 700,
        fontSize: count >= 100 ? '13px' : '12px',
        lineHeight: 1,
        cursor: 'pointer',
        transition: 'transform 0.2s ease, box-shadow 0.2s ease',
      }}
    >
      <span>{displayCount}</span>
      {segments.length > 0 && (
        <div
          style={{
            marginTop: '2px',
            width: '80%',
            height: '4px',
            borderRadius: '2px',
            overflow: 'hidden',
            display: 'flex',
          }}
        >
          {segments.map((seg, i) => (
            <div
              key={i}
              style={{
                width: `${seg.width}%`,
                height: '100%',
                background: seg.color,
                display: 'inline-block',
              }}
            />
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * Get cluster type summary for popup
 */
export function getClusterTypeSummary(distribution: Map<string, number>): string {
  const sortedTypes = Array.from(distribution.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5);

  return sortedTypes.map(([type, percentage]) => `${type}: ${percentage.toFixed(0)}%`).join(' • ');
}
