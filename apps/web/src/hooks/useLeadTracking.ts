/**
 * React hook for lead tracking.
 *
 * Provides easy-to-use tracking functions for React components.
 */

'use client';

import { useCallback, useEffect, useMemo, useRef } from 'react';

import {
  getOrCreateVisitorId,
  trackInteraction,
  trackSearch as trackSearchApi,
  trackPropertyView as trackPropertyViewApi,
  trackFavorite as trackFavoriteApi,
  trackInquiry as trackInquiryApi,
  trackContactRequest as trackContactRequestApi,
  trackViewingScheduled as trackViewingScheduledApi,
  trackSavedSearch as trackSavedSearchApi,
  trackReportDownload as trackReportDownloadApi,
  trackPropertyShare as trackPropertyShareApi,
  InteractionType,
} from '@/lib/visitor-tracking';

/**
 * Hook return type
 */
interface UseLeadTrackingReturn {
  /** Get the current visitor ID */
  visitorId: string;
  /** Track a generic interaction */
  trackInteraction: typeof trackInteraction;
  /** Track a search */
  trackSearch: (query: string, filters?: Record<string, unknown>) => Promise<void>;
  /** Track a property view with automatic time tracking */
  trackPropertyView: (propertyId: string) => { stopTracking: () => void };
  /** Track a favorite action */
  trackFavorite: (propertyId: string, action?: 'add' | 'remove') => Promise<void>;
  /** Track an inquiry */
  trackInquiry: (propertyId: string, hasMessage?: boolean) => Promise<void>;
  /** Track a contact request */
  trackContactRequest: (
    contactType: 'email' | 'phone' | 'callback',
    propertyId?: string
  ) => Promise<void>;
  /** Track a viewing scheduled */
  trackViewingScheduled: (propertyId: string) => Promise<void>;
  /** Track a saved search */
  trackSavedSearch: (searchId: string, query: string) => Promise<void>;
  /** Track a report download */
  trackReportDownload: (reportType: string) => Promise<void>;
  /** Track a property share */
  trackPropertyShare: (propertyId: string, shareMethod: string) => Promise<void>;
}

/**
 * Hook for lead tracking functionality.
 *
 * @example
 * ```tsx
 * const { trackPropertyView, trackSearch } = useLeadTracking();
 *
 * // Track a property view with automatic time tracking
 * const { stopTracking } = trackPropertyView('property-123');
 *
 * // Later, when user navigates away:
 * useEffect(() => {
 *   return () => stopTracking();
 * }, []);
 *
 * // Track a search
 * await trackSearch('2-bedroom apartment in Berlin', { price_max: 500000 });
 * ```
 */
export function useLeadTracking(): UseLeadTrackingReturn {
  // `getOrCreateVisitorId` needs `document`, so it cannot run during the server
  // render of a client component. Resolve it lazily on the client instead of
  // throwing, so this hook is safe to use in any component.
  const visitorId = useMemo(() => {
    if (typeof document === 'undefined') return '';
    try {
      return getOrCreateVisitorId();
    } catch {
      return '';
    }
  }, []);
  const viewStartTimeRef = useRef<number | null>(null);

  // Track property view with time tracking
  const trackPropertyView = useCallback((propertyId: string) => {
    // Start tracking time
    viewStartTimeRef.current = Date.now();

    // Track the view
    trackPropertyViewApi(propertyId);

    // Return stop function to calculate time spent
    return {
      stopTracking: () => {
        if (viewStartTimeRef.current) {
          const timeSpent = Math.round((Date.now() - viewStartTimeRef.current) / 1000);
          // Track again with time spent
          trackInteraction({
            interaction_type: 'view' as InteractionType,
            property_id: propertyId,
            time_spent_seconds: timeSpent,
          });
          viewStartTimeRef.current = null;
        }
      },
    };
  }, []);

  // Track search
  const trackSearch = useCallback(async (query: string, filters?: Record<string, unknown>) => {
    await trackSearchApi(query, filters);
  }, []);

  // Track favorite
  const trackFavorite = useCallback(
    async (propertyId: string, action: 'add' | 'remove' = 'add') => {
      await trackFavoriteApi(propertyId, action);
    },
    []
  );

  // Track inquiry
  const trackInquiry = useCallback(async (propertyId: string, hasMessage: boolean = true) => {
    await trackInquiryApi(propertyId, hasMessage);
  }, []);

  // Track contact request
  const trackContactRequest = useCallback(
    async (contactType: 'email' | 'phone' | 'callback', propertyId?: string) => {
      await trackContactRequestApi(contactType, propertyId);
    },
    []
  );

  // Track viewing scheduled
  const trackViewingScheduled = useCallback(async (propertyId: string) => {
    await trackViewingScheduledApi(propertyId);
  }, []);

  // Track saved search
  const trackSavedSearch = useCallback(async (searchId: string, query: string) => {
    await trackSavedSearchApi(searchId, query);
  }, []);

  // Track report download
  const trackReportDownload = useCallback(async (reportType: string) => {
    await trackReportDownloadApi(reportType);
  }, []);

  // Track property share
  const trackPropertyShare = useCallback(async (propertyId: string, shareMethod: string) => {
    await trackPropertyShareApi(propertyId, shareMethod);
  }, []);

  return {
    visitorId,
    trackInteraction,
    trackSearch,
    trackPropertyView,
    trackFavorite,
    trackInquiry,
    trackContactRequest,
    trackViewingScheduled,
    trackSavedSearch,
    trackReportDownload,
    trackPropertyShare,
  };
}

/**
 * Hook to automatically track time spent on a page/component.
 *
 * @param pageName - Name of the page to track
 * @param metadata - Additional metadata to track
 *
 * @example
 * ```tsx
 * function PropertyDetailPage({ propertyId }: { propertyId: string }) {
 *   useTrackPageTime('property_detail', { property_id: propertyId });
 *   // ...
 * }
 * ```
 */
export function useTrackPageTime(pageName: string, metadata?: Record<string, unknown>): void {
  const startTimeRef = useRef<number | null>(null);

  useEffect(() => {
    startTimeRef.current = Date.now();

    return () => {
      if (!startTimeRef.current) return;
      const timeSpent = Math.round((Date.now() - startTimeRef.current) / 1000);
      // Only track if spent at least 1 second
      if (timeSpent >= 1) {
        trackInteraction({
          interaction_type: 'page_view' as InteractionType,
          metadata: {
            page_name: pageName,
            time_spent_seconds: timeSpent,
            ...metadata,
          },
        });
      }
    };
  }, [pageName, metadata]);
}

/**
 * Hook to track search queries with debounce.
 *
 * @param debounceMs - Debounce time in milliseconds (default: 1000)
 *
 * @example
 * ```tsx
 * function SearchPage() {
 *   const { trackSearchDebounced, flushSearch } = useTrackSearchDebounced(500);
 *
 *   const handleSearch = (query: string) => {
 *     trackSearchDebounced(query, filters);
 *   };
 *
 *   // Flush pending search on unmount
 *   useEffect(() => {
 *     return () => flushSearch();
 *   }, []);
 * }
 * ```
 */
export function useTrackSearchDebounced(debounceMs: number = 1000): {
  trackSearchDebounced: (query: string, filters?: Record<string, unknown>) => void;
  flushSearch: () => void;
} {
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pendingRef = useRef<{ query: string; filters?: Record<string, unknown> } | null>(null);

  const flushSearch = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    if (pendingRef.current) {
      trackSearchApi(pendingRef.current.query, pendingRef.current.filters);
      pendingRef.current = null;
    }
  }, []);

  const trackSearchDebounced = useCallback(
    (query: string, filters?: Record<string, unknown>) => {
      pendingRef.current = { query, filters };

      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }

      timeoutRef.current = setTimeout(() => {
        if (pendingRef.current) {
          trackSearchApi(pendingRef.current.query, pendingRef.current.filters);
          pendingRef.current = null;
        }
      }, debounceMs);
    },
    [debounceMs]
  );

  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  return { trackSearchDebounced, flushSearch };
}
