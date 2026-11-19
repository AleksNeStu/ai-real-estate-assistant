/**
 * Visitor tracking library for lead scoring.
 *
 * Provides cookie-based visitor identification and interaction tracking
 * for the lead scoring system.
 */

import { isValidLocale } from '@/i18n/config';

// Cookie configuration
const VISITOR_ID_COOKIE = 'visitor_id';
const VISITOR_ID_MAX_AGE = 365 * 24 * 60 * 60 * 1000; // 365 days in seconds

/**
 * Generate a new unique visitor ID.
 */
export function generateVisitorId(): string {
  // Use crypto API if available, otherwise fallback to UUID v4
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  // Fallback for older browsers — primary path uses crypto.randomUUID()
  // nosemgrep: weak-random.random — non-security visitor ID, crypto.randomUUID() preferred
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0; // nosemgrep: weak-random.random
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

/**
 * Get visitor ID from cookies (server-side).
 */
export function getVisitorIdFromCookies(cookieHeader: string | null | undefined): string | null {
  if (!cookieHeader) return null;

  const cookies = cookieHeader.split(';');
  for (const cookie of cookies) {
    const [name, value] = cookie.trim().split('=');
    if (name === VISITOR_ID_COOKIE && value) {
      return value;
    }
  }
  return null;
}

/**
 * Set visitor ID cookie in response headers.
 */
export function setVisitorIdCookie(visitorId: string): string {
  return `${VISITOR_ID_COOKIE}=${visitorId}; Path=/; Max-Age=${VISITOR_ID_MAX_AGE}; SameSite=Lax; Secure`;
}

/**
 * Get or create visitor ID from client-side cookies.
 * This should only be used in client components.
 */
export function getOrCreateVisitorId(): string {
  if (typeof document === 'undefined') {
    throw new Error('getOrCreateVisitorId can only be used in client components');
  }

  // Check existing cookie
  const existing = getCookie(VISITOR_ID_COOKIE);
  if (existing) return existing;

  // Create new visitor ID
  const newId = generateVisitorId();
  setCookie(VISITOR_ID_COOKIE, newId, VISITOR_ID_MAX_AGE);
  return newId;
}

/**
 * Get a cookie value (client-side).
 */
function getCookie(name: string): string | null {
  if (typeof document === 'undefined') return null;

  const cookies = document.cookie.split(';');
  for (const cookie of cookies) {
    const [cookieName, cookieValue] = cookie.trim().split('=');
    if (cookieName === name && cookieValue) {
      return decodeURIComponent(cookieValue);
    }
  }
  return null;
}

/**
 * Set a cookie value (client-side).
 */
function setCookie(name: string, value: string, maxAge: number): void {
  if (typeof document === 'undefined') return;

  const expires = new Date(Date.now() + maxAge * 1000).toUTCString();
  document.cookie = `${name}=${encodeURIComponent(value)}; Path=/; Expires=${expires}; SameSite=Lax; Secure`;
}

// Interaction type enum (matches backend)
export type InteractionType =
  | 'search'
  | 'view'
  | 'favorite'
  | 'unfavorite'
  | 'inquiry'
  | 'contact'
  | 'schedule_viewing'
  | 'download_report'
  | 'share'
  | 'save_search'
  | 'unsave_search'
  | 'login'
  | 'register'
  | 'profile_update';

/**
 * The locale of a path, read from its first segment.
 *
 * Every page of the site lives under a locale segment (`/pl/properties`,
 * `/en/properties`), so the locale is known where the route is - and nowhere
 * else. A path that does not begin with a locale carries none.
 */
export function parseLocaleFromPath(pathname: string | null | undefined): string | null {
  if (!pathname) return null;
  const segment = pathname.split('/').filter(Boolean)[0];
  return segment && isValidLocale(segment) ? segment : null;
}

/**
 * The locale of the page the browser is on.
 */
export function currentLocale(): string | null {
  if (typeof window === 'undefined') return null;
  return parseLocaleFromPath(window.location.pathname);
}

/**
 * Track a visitor interaction.
 * Sends the interaction to the backend for lead scoring.
 */
export async function trackInteraction(event: {
  interaction_type: InteractionType;
  property_id?: string;
  search_query?: string;
  metadata?: Record<string, unknown>;
  session_id?: string;
  page_url?: string;
  referrer?: string;
  time_spent_seconds?: number;
  locale?: string;
}): Promise<void> {
  const visitor_id = getOrCreateVisitorId();
  // The locale is the route's own segment, so it is read here - where the
  // route is - and sent as its own field. A page that is not under a
  // locale sends none: the field is optional.
  const locale = event.locale ?? currentLocale();

  try {
    await fetch('/api/v1/leads/track', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        visitor_id,
        ...event,
        locale: locale ?? undefined,
        page_url:
          event.page_url || (typeof window !== 'undefined' ? window.location.href : undefined),
        referrer:
          event.referrer || (typeof document !== 'undefined' ? document.referrer : undefined),
      }),
    });
  } catch (error) {
    // Silently fail - tracking should not break user experience
    console.error('Failed to track interaction:', error);
  }
}

/**
 * Track a search interaction.
 */
export async function trackSearch(query: string, filters?: Record<string, unknown>): Promise<void> {
  await trackInteraction({
    interaction_type: 'search',
    search_query: query,
    metadata: { filters },
  });
}

/**
 * Track a property view.
 */
export async function trackPropertyView(
  propertyId: string,
  timeSpentSeconds?: number
): Promise<void> {
  await trackInteraction({
    interaction_type: 'view',
    property_id: propertyId,
    time_spent_seconds: timeSpentSeconds,
  });
}

/**
 * Track a favorite action.
 */
export async function trackFavorite(
  propertyId: string,
  action: 'add' | 'remove' = 'add'
): Promise<void> {
  await trackInteraction({
    interaction_type: action === 'add' ? 'favorite' : 'unfavorite',
    property_id: propertyId,
    metadata: { action },
  });
}

/**
 * Track an inquiry submission.
 */
export async function trackInquiry(propertyId: string, hasMessage: boolean): Promise<void> {
  await trackInteraction({
    interaction_type: 'inquiry',
    property_id: propertyId,
    metadata: { has_message: hasMessage },
  });
}

/**
 * Track a contact request.
 */
export async function trackContactRequest(
  contactType: 'email' | 'phone' | 'callback',
  propertyId?: string
): Promise<void> {
  await trackInteraction({
    interaction_type: 'contact',
    property_id: propertyId,
    metadata: { contact_type: contactType },
  });
}

/**
 * Track a viewing schedule.
 */
export async function trackViewingScheduled(propertyId: string): Promise<void> {
  await trackInteraction({
    interaction_type: 'schedule_viewing',
    property_id: propertyId,
  });
}

/**
 * Track a saved search.
 */
export async function trackSavedSearch(searchId: string, query: string): Promise<void> {
  await trackInteraction({
    interaction_type: 'save_search',
    search_query: query,
    metadata: { search_id: searchId },
  });
}

/**
 * Track a report download.
 */
export async function trackReportDownload(reportType: string): Promise<void> {
  await trackInteraction({
    interaction_type: 'download_report',
    metadata: { report_type: reportType },
  });
}

/**
 * Track a property share.
 */
export async function trackPropertyShare(propertyId: string, shareMethod: string): Promise<void> {
  await trackInteraction({
    interaction_type: 'share',
    property_id: propertyId,
    metadata: { share_method: shareMethod },
  });
}

/**
 * Track user login (links visitor to user).
 */
export async function trackLogin(): Promise<void> {
  await trackInteraction({
    interaction_type: 'login',
  });
}

/**
 * Track user registration.
 */
export async function trackRegister(): Promise<void> {
  await trackInteraction({
    interaction_type: 'register',
  });
}

/**
 * Track profile update.
 */
export async function trackProfileUpdate(fields: string[]): Promise<void> {
  await trackInteraction({
    interaction_type: 'profile_update',
    metadata: { updated_fields: fields },
  });
}
