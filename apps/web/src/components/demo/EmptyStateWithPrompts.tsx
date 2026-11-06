'use client';

import { useTranslations } from 'next-intl';
import { Search } from 'lucide-react';
import { TryTheseChips } from './TryTheseChips';

interface EmptyStateWithPromptsProps {
  /** Title of the empty state. Falls back to next-intl `common.emptySearchTitle`. */
  title?: string;
  /** Body of the empty state. Falls back to next-intl `common.emptySearchBody`. */
  body?: string;
  /** Locale-prefixed search path passed through to TryTheseChips. */
  searchHref?: string;
  className?: string;
}

/**
 * Reusable empty state for routes that have nothing to show yet
 * (`/search` no-query, `/market-trends` no-data, `/valuation` no-input).
 *
 * Renders an icon, title, body, and TryTheseChips so first-time visitors
 * always have a next action.
 *
 * Localization: passes through to next-intl `common` namespace; English
 * fallback used when keys are absent in the locale.
 */
export function EmptyStateWithPrompts({
  title,
  body,
  searchHref,
  className,
}: EmptyStateWithPromptsProps) {
  const t = useTranslations('common');
  const resolvedTitle = title ?? t('emptySearchTitle') ?? 'Nothing to show yet';
  const resolvedBody =
    body ??
    t('emptySearchBody') ??
    'Try one of the example queries below to see the demo in action.';

  return (
    <div
      className={`flex flex-col items-center justify-center text-center py-12 px-4 ${className ?? ''}`}
      role="status"
    >
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted/40 mb-4">
        <Search className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
      </div>
      <h3 className="text-base font-semibold text-foreground mb-1">
        {resolvedTitle}
      </h3>
      <p className="text-sm text-muted-foreground max-w-md mb-6">
        {resolvedBody}
      </p>
      <TryTheseChips searchHref={searchHref} />
    </div>
  );
}