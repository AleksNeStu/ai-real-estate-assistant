'use client';

import { ChartFrame } from '@/components/ui/chart-frame';
import { MonoAnnotation } from '@/components/ui/mono-annotation';
import { cn } from '@/lib/utils';

/**
 * The daily activity, as a row of bars.
 *
 * The chart is a bar per day, the way the design draws it: a thin column
 * standing on a rule, the last one in ink and the rest at half the ink.
 * The frame holds the space, so the row does not move when the numbers
 * arrive.
 */

export interface ActivityPoint {
  /** The day, as the API states it. */
  date: string;
  /** What happened that day. */
  value: number;
}

export interface UsageActivityChartProps {
  points: ActivityPoint[];
  /** The title of the chart. */
  title: string;
  /** The mono note beside the title: the period, the source. */
  caption?: string;
  /** The first and last day, stated under the bars. */
  axisLabels?: { first: string; last: string };
  className?: string;
}

export function UsageActivityChart({
  points,
  title,
  caption,
  axisLabels,
  className,
}: UsageActivityChartProps) {
  const max = points.reduce((highest, point) => Math.max(highest, point.value), 0);

  return (
    <ChartFrame title={title} caption={caption} height={140} className={className}>
      <div className="flex h-[120px] items-end gap-[4px] border-b border-border">
        {points.map((point, index) => {
          const height = max > 0 ? Math.round((point.value / max) * 100) : 0;
          const isLast = index === points.length - 1;
          return (
            <div
              key={`${point.date}-${index}`}
              title={`${point.date}: ${point.value}`}
              data-testid="usage-bar"
              className={cn(
                'flex-1 rounded-t-[2px] bg-foreground',
                !isLast && 'opacity-55'
              )}
              style={{ height: `${Math.max(height, point.value > 0 ? 2 : 0)}%` }}
            />
          );
        })}
      </div>
      {axisLabels ? (
        <div className="mt-[-12px] flex justify-between">
          <MonoAnnotation>{axisLabels.first}</MonoAnnotation>
          <MonoAnnotation>{axisLabels.last}</MonoAnnotation>
        </div>
      ) : null}
    </ChartFrame>
  );
}
