'use client';

import { FlaskConical } from 'lucide-react';
import { useTranslations } from 'next-intl';

interface DemoDataBadgeProps {
  variant?: 'card' | 'inline';
  className?: string;
}

/**
 * Visual marker that a card / row / panel contains demo data (not real
 * listings). Renders as a small pill with a flask icon.
 *
 * Two variants:
 *  - `card` — for property cards, comparable to price / sqm badges
 *  - `inline` — for empty-state or section headers
 *
 * Purely decorative; non-interactive. Provides tooltip via `title` for
 * accessibility on hover.
 */
export function DemoDataBadge({
  variant = 'card',
  className,
}: DemoDataBadgeProps) {
  const t = useTranslations('demo');
  const label = t('badgeTooltip');

  const base =
    'inline-flex items-center gap-1 rounded-full bg-warning/10 text-warning dark:text-caution border border-caution/20';

  const sizes =
    variant === 'card' ? 'px-2 py-0.5 text-[10px]' : 'px-2.5 py-1 text-xs';

  return (
    <span
      className={`${base} ${sizes} ${className ?? ''}`}
      title={label}
      aria-label={label}
    >
      <FlaskConical className="h-3 w-3" aria-hidden="true" />
      <span className="font-medium uppercase tracking-wide">{t('badgeLabel')}</span>
    </span>
  );
}
