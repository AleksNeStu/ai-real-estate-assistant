'use client';

import { useLocale, useTranslations } from 'next-intl';

import { ChartFrame } from '@/components/ui/chart-frame';
import { formatPrice } from '@/lib/format';
import type { ForecastPoint, PriceForecastResponse } from '@/lib/api/tools';

/**
 * The forecast, drawn.
 *
 * An inline SVG rather than a chart library: the public demo must stay
 * small, and the shape is simple - a line, a band under it, and the
 * horizon labels.
 *
 * The band is the API's own lower and upper bound, drawn as one polygon
 * under the line. The line is ink, not a chart colour: the design keeps the
 * chrome zinc and lets one accent carry the single primary action.
 */

const VIEW_WIDTH = 800;
const VIEW_HEIGHT = 220;
const PADDING_X = 40;
const PADDING_Y = 24;
const BASELINE_Y = 200;

interface PlotPoint {
  years_ahead: number;
  estimated_value: number;
  lower: number;
  upper: number;
}

export interface ForecastChartProps {
  result: PriceForecastResponse;
  className?: string;
}

export function ForecastChart({ result, className }: ForecastChartProps) {
  const t = useTranslations('pages.valuation');
  const locale = useLocale();
  const currency = result.currency || 'EUR';

  const points: PlotPoint[] = [
    {
      years_ahead: 0,
      estimated_value: result.current_estimate,
      lower: result.current_estimate,
      upper: result.current_estimate,
    },
    ...result.forecast.map((point: ForecastPoint) => ({
      years_ahead: point.years_ahead,
      estimated_value: point.estimated_value,
      lower: point.lower_bound,
      upper: point.upper_bound,
    })),
  ];

  const tCaption = t('chart.caption', { horizons: result.forecast.length });

  if (points.length < 2) {
    return (
      <ChartFrame title={t('chart.title')} caption={tCaption} className={className}>
        <p className="text-[14px] text-muted-foreground">{t('chart.empty')}</p>
      </ChartFrame>
    );
  }

  const minX = points[0].years_ahead;
  const maxX = Math.max(...points.map((point) => point.years_ahead));
  const allValues = points.flatMap((point) => [point.lower, point.estimated_value, point.upper]);
  const minY = Math.min(...allValues);
  const maxY = Math.max(...allValues);
  const span = Math.max(maxY - minY, 1);

  const x = (years: number) =>
    PADDING_X +
    ((years - minX) / Math.max(maxX - minX, 1)) * (VIEW_WIDTH - 2 * PADDING_X);
  const y = (value: number) =>
    BASELINE_Y -
    ((value - minY) / span) * (BASELINE_Y - PADDING_Y - 8);

  const upperPath = points.map((point) => `${x(point.years_ahead)},${y(point.upper)}`);
  const lowerPath = [...points]
    .reverse()
    .map((point) => `${x(point.years_ahead)},${y(point.lower)}`);
  const bandPath = `M ${upperPath.join(' L ')} L ${lowerPath.join(' L ')} Z`;

  const linePath = points
    .map(
      (point, index) =>
        `${index === 0 ? 'M' : 'L'} ${x(point.years_ahead)},${y(point.estimated_value)}`
    )
    .join(' ');

  return (
    <ChartFrame
      title={t('chart.title')}
      caption={tCaption}
      height={VIEW_HEIGHT}
      className={className}
    >
      <svg
        viewBox={`0 0 ${VIEW_WIDTH} ${VIEW_HEIGHT}`}
        className="block w-full"
        role="img"
        aria-label={t('chart.aria')}
        data-testid="valuation-forecast-chart"
      >
        <line
          x1={PADDING_X}
          y1={BASELINE_Y}
          x2={VIEW_WIDTH - PADDING_X}
          y2={BASELINE_Y}
          className="stroke-border"
          strokeWidth={1}
        />
        <path d={bandPath} fill="currentColor" fillOpacity={0.08} />
        <path
          d={linePath}
          fill="none"
          stroke="currentColor"
          strokeWidth={2.2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {points.map((point) => (
          <circle
            key={point.years_ahead}
            cx={x(point.years_ahead)}
            cy={y(point.estimated_value)}
            r={point.years_ahead === 0 ? 4 : 3}
            fill="currentColor"
          >
            <title>
              {point.years_ahead === 0
                ? t('result.today')
                : t('result.yearsLabel', { years: point.years_ahead })}
              : {formatPrice(point.estimated_value, currency, locale)}
            </title>
          </circle>
        ))}
        {points.map((point) => (
          <text
            key={`x-${point.years_ahead}`}
            x={x(point.years_ahead)}
            y={VIEW_HEIGHT - 2}
            textAnchor={point.years_ahead === maxX ? 'end' : 'middle'}
            className="fill-muted-foreground font-mono"
            fontSize={11}
          >
            {point.years_ahead === 0
              ? t('result.today')
              : t('result.yearsShort', { years: point.years_ahead })}
          </text>
        ))}
      </svg>
    </ChartFrame>
  );
}
