import type { ReactNode } from 'react';

import { MonoAnnotation } from '@/components/ui/mono-annotation';
import { cn } from '@/lib/utils';

/**
 * The height a chart area reserves, in pixels.
 *
 * The area is reserved on purpose: a chart that arrives late must not push
 * the page down when it lands.
 */
const DEFAULT_CHART_HEIGHT = 240;

/**
 * The frame around a chart.
 *
 * A panel with a hairline border, a title on the left, a mono caption on the
 * right (the period, the unit, the city), and the chart's own space held
 * open underneath. Flat, with hairlines - the chart is the only thing in
 * here that carries a colour.
 */
export interface ChartFrameProps {
  /** What the chart shows. */
  title: ReactNode;
  /** The mono note beside the title: the period, the source, the unit. */
  caption?: ReactNode;
  /** The chart itself. */
  children?: ReactNode;
  /** The height the frame reserves for the chart, in pixels. */
  height?: number;
  className?: string;
}

export function ChartFrame({
  title,
  caption,
  children,
  height = DEFAULT_CHART_HEIGHT,
  className,
}: ChartFrameProps) {
  return (
    <figure className={cn('flex flex-col gap-2.5 rounded-lg border border-border p-4', className)}>
      <figcaption className="flex items-baseline justify-between gap-4">
        <span className="font-semibold text-app text-foreground">{title}</span>
        {caption ? (
          <MonoAnnotation className="shrink-0 text-right">{caption}</MonoAnnotation>
        ) : null}
      </figcaption>
      <div
        className="relative w-full"
        data-testid="chart-frame-area"
        style={{ minHeight: height }}
      >
        {children}
      </div>
    </figure>
  );
}
