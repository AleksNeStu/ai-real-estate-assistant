'use client';

import { ChartFrame } from '@/components/ui/chart-frame';
import { MonoAnnotation } from '@/components/ui/mono-annotation';
import { cn } from '@/lib/utils';

/**
 * The deals per month.
 *
 * One bar per month, the way the design draws it: a thin column standing on
 * a rule, the newest in ink and the rest in the muted chrome. The frame
 * holds the space, so the row does not move when the numbers arrive.
 */

export interface TrendPoint {
  /** The period, as the API states it. */
  period: string;
  /** What was closed in it. */
  value: number;
}

export interface AgentTrendChartProps {
  points: TrendPoint[];
  title: string;
  caption?: string;
  className?: string;
}

export function AgentTrendChart({ points, title, caption, className }: AgentTrendChartProps) {
  const max = points.reduce((highest, point) => Math.max(highest, point.value), 0);

  return (
    <ChartFrame title={title} caption={caption} height={150} className={className}>
      <div className="flex h-[120px] items-end gap-2 border-b border-border">
        {points.map((point, index) => {
          const height = max > 0 ? Math.round((point.value / max) * 100) : 0;
          const isLast = index === points.length - 1;
          return (
            <div
              key={`${point.period}-${index}`}
              title={`${point.period}: ${point.value}`}
              data-testid="agent-trend-bar"
              className="flex h-full flex-1 flex-col items-center justify-end gap-1"
            >
              <MonoAnnotation>{point.value}</MonoAnnotation>
              <div
                className={cn('w-full rounded-t-[2px] bg-foreground', !isLast && 'opacity-55')}
                style={{ height: `${Math.max(height, point.value > 0 ? 2 : 0)}%` }}
              />
            </div>
          );
        })}
      </div>
    </ChartFrame>
  );
}
