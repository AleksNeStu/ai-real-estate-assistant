'use client';

import React, { useState } from 'react';
import { useTranslations } from 'next-intl';
import { ThumbsUp, ThumbsDown } from 'lucide-react';
import { submitFeedback } from '@/lib/api';

interface RelevanceRatingProps {
  /** The search query that produced this result */
  query: string;
  /** The property ID being rated */
  propertyId: string;
}

export function RelevanceRating({ query, propertyId }: RelevanceRatingProps) {
  const t = useTranslations('search.feedback');
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  const handleRate = async (rating: number) => {
    if (loading || submitted) return;
    setLoading(true);
    setError(false);
    try {
      await submitFeedback(query, propertyId, rating);
      setSubmitted(true);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  if (submitted) {
    return <p className="text-xs text-muted-foreground italic">{t('thanks')}</p>;
  }

  return (
    <div className="flex items-center gap-1">
      <span className="text-xs text-muted-foreground mr-1">{t('helpful')}</span>
      <button
        type="button"
        onClick={() => handleRate(5)}
        disabled={loading}
        className="p-1 rounded hover:bg-success/15 dark:hover:bg-success/30 disabled:opacity-50 transition-colors"
        aria-label={t('thumbsUp')}
        title={t('thumbsUp')}
      >
        <ThumbsUp className="h-4 w-4 text-success dark:text-success" />
      </button>
      <button
        type="button"
        onClick={() => handleRate(1)}
        disabled={loading}
        className="p-1 rounded hover:bg-destructive/15 dark:hover:bg-destructive/30 disabled:opacity-50 transition-colors"
        aria-label={t('thumbsDown')}
        title={t('thumbsDown')}
      >
        <ThumbsDown className="h-4 w-4 text-destructive dark:text-destructive" />
      </button>
      {error && <span className="text-xs text-destructive ml-1">{t('error')}</span>}
    </div>
  );
}
