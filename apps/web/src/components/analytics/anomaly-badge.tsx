'use client';

import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';
import type { AnomalySeverity, AnomalyType } from '@/lib/types';
import { useTranslations } from 'next-intl';

const anomalySeverityVariants = cva(
  'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors',
  {
    variants: {
      severity: {
        low: 'border-transparent bg-muted text-muted-foreground',
        medium: 'border-transparent bg-warning/20 text-warning',
        high: 'border-transparent bg-caution/20 text-caution',
        critical: 'border-transparent bg-destructive/20 text-destructive',
      },
    },
    defaultVariants: {
      severity: 'low',
    },
  }
);

const anomalyTypeVariants = cva(
  'inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium',
  {
    variants: {
      type: {
        price_spike: 'bg-chart-1/10 text-chart-1',
        price_drop: 'bg-chart-2/10 text-chart-2',
        volume_spike: 'bg-chart-4/10 text-chart-4',
        volume_drop: 'bg-chart-3/10 text-chart-3',
        unusual_pattern: 'bg-chart-5/10 text-chart-5',
      },
    },
    defaultVariants: {
      type: 'unusual_pattern',
    },
  }
);

export interface AnomalySeverityBadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>, VariantProps<typeof anomalySeverityVariants> {
  severity: AnomalySeverity;
}

export function AnomalySeverityBadge({ severity, className, ...props }: AnomalySeverityBadgeProps) {
  const t = useTranslations('marketTrends');
  const labels: Record<AnomalySeverity, string> = {
    low: t('anomalies.severities.low'),
    medium: t('anomalies.severities.medium'),
    high: t('anomalies.severities.high'),
    critical: t('anomalies.severities.critical'),
  };

  return (
    <span className={cn(anomalySeverityVariants({ severity }), className)} {...props}>
      {labels[severity]}
    </span>
  );
}

export interface AnomalyTypeBadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>, VariantProps<typeof anomalyTypeVariants> {
  type: AnomalyType;
}

export function AnomalyTypeBadge({ type, className, ...props }: AnomalyTypeBadgeProps) {
  const t = useTranslations('marketTrends');
  const labels: Record<AnomalyType, string> = {
    price_spike: t('anomalies.types.priceSpike'),
    price_drop: t('anomalies.types.priceDrop'),
    volume_spike: t('anomalies.types.volumeSpike'),
    volume_drop: t('anomalies.types.volumeDrop'),
    unusual_pattern: t('anomalies.types.unusualPattern'),
  };

  const icons: Record<AnomalyType, React.ReactNode> = {
    price_spike: (
      <svg
        className="h-3 w-3"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"
        />
      </svg>
    ),
    price_drop: (
      <svg
        className="h-3 w-3"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6"
        />
      </svg>
    ),
    volume_spike: (
      <svg
        className="h-3 w-3"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
        />
      </svg>
    ),
    volume_drop: (
      <svg
        className="h-3 w-3"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2zm6 0v-4a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
        />
      </svg>
    ),
    unusual_pattern: (
      <svg
        className="h-3 w-3"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
        />
      </svg>
    ),
  };

  return (
    <span className={cn(anomalyTypeVariants({ type }), className)} {...props}>
      {icons[type]}
      {labels[type]}
    </span>
  );
}

export { anomalySeverityVariants, anomalyTypeVariants };

// Combined badge for showing both severity and type
export interface AnomalyBadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  severity: AnomalySeverity;
  type?: AnomalyType;
  size?: 'sm' | 'default';
}

export function AnomalyBadge({
  severity,
  type,
  size = 'default',
  className,
  ...props
}: AnomalyBadgeProps) {
  const sizeClasses = size === 'sm' ? 'text-xs px-2 py-0.5' : 'text-xs px-2.5 py-0.5';

  return (
    <div className={cn('flex items-center gap-1', className)} {...props}>
      <AnomalySeverityBadge severity={severity} className={sizeClasses} />
      {type && <AnomalyTypeBadge type={type} className={sizeClasses} />}
    </div>
  );
}

// Severity icon helper
export function getSeverityIcon(severity: AnomalySeverity) {
  const icons: Record<AnomalySeverity, React.ComponentType<{ className?: string }>> = {
    low: function LowIcon({ className }) {
      return (
        <svg
          className={className}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      );
    },
    medium: function MediumIcon({ className }) {
      return (
        <svg
          className={className}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
          />
        </svg>
      );
    },
    high: function HighIcon({ className }) {
      return (
        <svg
          className={className}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      );
    },
    critical: function CriticalIcon({ className }) {
      return (
        <svg
          className={className}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M20.618 5.984A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016zM12 9v2m0 4h.01"
          />
        </svg>
      );
    },
  };
  return icons[severity];
}
