'use client';

import React, { useState } from 'react';
import { Heart, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

import { useTranslations } from 'next-intl';
import { useRouter } from '@/i18n/navigation';
import { cn } from '@/lib/utils';
import { useFavorites } from '@/contexts/FavoritesContext';
import { useAuth } from '@/contexts/AuthContext';

interface HeartButtonProps {
  propertyId: string;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
  showTooltip?: boolean;
  onToggle?: (isFavorited: boolean) => void;
}

export function HeartButton({
  propertyId,
  className,
  size = 'md',
  showTooltip = true,
  onToggle,
}: HeartButtonProps) {
  const { isAuthenticated } = useAuth();
  const { isFavorited, toggleFavorite } = useFavorites();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const t = useTranslations('property.card');
  const tCommon = useTranslations('common');
  const router = useRouter();

  const favorited = isFavorited(propertyId);

  const sizeClasses = {
    sm: 'h-4 w-4',
    md: 'h-5 w-5',
    lg: 'h-6 w-6',
  };

  const handleClick = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();

    if (!isAuthenticated) {
      // The old behaviour only wrote the message into a screen-reader-only
      // element, so a signed-out visitor clicked the heart and nothing
      // happened. The message is now visible, and it offers the way out.
      const message = t('loginRequired');
      setError(message);
      toast.error(message, {
        action: {
          label: tCommon('logIn'),
          onClick: () => router.push('/auth/login'),
        },
      });
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const newState = await toggleFavorite(propertyId);
      onToggle?.(newState);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : tCommon('error');
      setError(message);
      toast.error(message);
    } finally {
      setIsLoading(false);
    }
  };

  const label = favorited ? t('removeFromFavorites') : t('addToFavorites');

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={isLoading}
      className={cn(
        'relative rounded-full p-2 transition-all duration-200',
        'bg-background/80 text-muted-foreground backdrop-blur-sm',
        'hover:bg-accent hover:text-foreground',
        'focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        className
      )}
      data-testid="favorite-toggle"
      title={showTooltip ? label : undefined}
      aria-label={label}
      aria-pressed={favorited}
    >
      {isLoading ? (
        <Loader2 className={cn(sizeClasses[size], 'animate-spin text-muted-foreground')} />
      ) : (
        <Heart
          className={cn(
            sizeClasses[size],
            'transition-colors duration-200',
            favorited
              ? 'fill-destructive text-destructive'
              : 'text-muted-foreground hover:text-destructive'
          )}
        />
      )}

      {error && (
        <span className="sr-only" role="alert">
          {error}
        </span>
      )}
    </button>
  );
}
