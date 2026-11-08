'use client';

import { useReducer, useEffect, useSyncExternalStore } from 'react';
import { WifiOff, Wifi } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { cn } from '@/lib/utils';

interface OfflineBannerProps {
  className?: string;
}

// Custom hook to subscribe to online/offline status
function useOnlineStatus() {
  const isOnline = useSyncExternalStore(
    (callback) => {
      if (typeof window === 'undefined') {
        return () => {};
      }
      window.addEventListener('online', callback);
      window.addEventListener('offline', callback);
      return () => {
        window.removeEventListener('online', callback);
        window.removeEventListener('offline', callback);
      };
    },
    () => {
      if (typeof navigator === 'undefined') {
        return true;
      }
      return navigator.onLine;
    },
    () => true // Server snapshot
  );
  return isOnline;
}

// State machine for banner
type BannerState = 'hidden' | 'offline' | 'restored';
type BannerAction = { type: 'GO_OFFLINE' } | { type: 'GO_ONLINE' } | { type: 'HIDE_RESTORED' };

function bannerReducer(state: BannerState, action: BannerAction): BannerState {
  switch (action.type) {
    case 'GO_OFFLINE':
      return 'offline';
    case 'GO_ONLINE':
      // Only show restored if we were previously offline
      return state === 'offline' ? 'restored' : 'hidden';
    case 'HIDE_RESTORED':
      return 'hidden';
    default:
      return state;
  }
}

/**
 * Offline Banner Component
 * Shows when the app is offline and hides when back online
 */
export function OfflineBanner({ className }: OfflineBannerProps) {
  const isOnline = useOnlineStatus();
  const [bannerState, dispatch] = useReducer(bannerReducer, 'hidden');
  const t = useTranslations('common');

  // Handle online/offline transitions
  useEffect(() => {
    if (!isOnline) {
      dispatch({ type: 'GO_OFFLINE' });
    } else {
      dispatch({ type: 'GO_ONLINE' });
    }
  }, [isOnline]);

  // Auto-hide restored message after 3 seconds
  useEffect(() => {
    if (bannerState === 'restored') {
      const timer = setTimeout(() => {
        dispatch({ type: 'HIDE_RESTORED' });
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [bannerState]);

  // Show restored message
  if (bannerState === 'restored') {
    return (
      <div
        role="status"
        aria-live="polite"
        className={cn(
          'fixed top-0 left-0 right-0 z-50 bg-success px-4 py-2 text-center text-sm text-success-foreground transition-all',
          className
        )}
      >
        <div className="flex items-center justify-center gap-2">
          <Wifi className="h-4 w-4" aria-hidden="true" />
          <span>{t('backOnline')}</span>
        </div>
      </div>
    );
  }

  // Show offline warning
  if (bannerState === 'offline') {
    return (
      <div
        role="status"
        aria-live="polite"
        className={cn(
          'fixed top-0 left-0 right-0 z-50 bg-caution px-4 py-2 text-center text-sm text-caution-foreground transition-all',
          className
        )}
      >
        <div className="flex items-center justify-center gap-2">
          <WifiOff className="h-4 w-4" aria-hidden="true" />
          <span>{t('offlineMessage')}</span>
        </div>
      </div>
    );
  }

  return null;
}
