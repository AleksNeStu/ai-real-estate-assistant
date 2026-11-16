/**
 * Base API client utilities: URL resolution, auth headers, error handling, fetch wrappers.
 *
 * All domain modules import from this file for shared infrastructure.
 */

/**
 * Error category for classification and handling.
 */
export type ApiErrorCategory =
  | 'network' // Connection failed, offline, DNS issues
  | 'timeout' // Request timed out
  | 'auth' // 401/403 authentication/authorization errors
  | 'validation' // 400/422 client-side validation errors
  | 'not_found' // 404 resource not found
  | 'rate_limit' // 429 too many requests
  | 'server' // 500+ server-side errors
  | 'unknown'; // Unclassified errors

/**
 * Custom error class for API errors that includes request_id for correlation
 * and error categorization for better handling strategies.
 *
 * @example
 * ```ts
 * try {
 *   await searchProperties({ query: "test" });
 * } catch (e) {
 *   if (e instanceof ApiError) {
 *     if (e.isRetryable) {
 *       // Implement retry logic
 *     }
 *     if (e.category === "auth") {
 *       // Redirect to login
 *     }
 *   }
 * }
 * ```
 */
export class ApiError extends Error {
  public readonly category: ApiErrorCategory;
  public readonly isRetryable: boolean;

  constructor(
    message: string,
    public readonly status: number,
    public readonly request_id?: string,
    category?: ApiErrorCategory
  ) {
    super(message);
    this.name = 'ApiError';

    // Determine category if not provided
    this.category = category ?? ApiError.categorizeStatus(status);

    // Determine if error is retryable
    this.isRetryable = ApiError.isRetryableCategory(this.category, status);
  }

  /**
   * Categorize error based on HTTP status code.
   */
  static categorizeStatus(status: number): ApiErrorCategory {
    if (status === 0) return 'network';
    if (status === 401 || status === 403) return 'auth';
    if (status === 404) return 'not_found';
    if (status === 408 || status === 504) return 'timeout';
    if (status === 429) return 'rate_limit';
    if (status === 400 || status === 422) return 'validation';
    if (status >= 500) return 'server';
    return 'unknown';
  }

  /**
   * Determine if an error category is generally retryable.
   * Network errors, timeouts, rate limits, and some server errors may be retried.
   */
  static isRetryableCategory(category: ApiErrorCategory, status: number): boolean {
    switch (category) {
      case 'network':
      case 'timeout':
      case 'rate_limit':
        return true;
      case 'server':
        // 503 Service Unavailable and 502 Bad Gateway are often transient
        return status === 502 || status === 503;
      default:
        return false;
    }
  }

  /**
   * Create a network error (for fetch failures, offline, etc.)
   */
  static networkError(originalError?: Error): ApiError {
    const message = originalError?.message || 'Network request failed. Check your connection.';
    const error = new ApiError(message, 0, undefined, 'network');
    if (originalError) {
      error.cause = originalError;
    }
    return error;
  }

  /**
   * Create a timeout error.
   */
  static timeoutError(request_id?: string): ApiError {
    return new ApiError('Request timed out. Please try again.', 408, request_id, 'timeout');
  }
}

export function getApiUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL || '/api/v1';
}

export function getUserEmail(): string | undefined {
  if (typeof window === 'undefined') return undefined;
  const email = window.localStorage.getItem('userEmail');
  return email && email.trim() ? email.trim() : undefined;
}

/**
 * The CSRF token the backend set at sign-in, read back from the cookie.
 *
 * The cookie is deliberately not httpOnly - the browser has to be able to
 * read it and send it back as the `X-CSRF-Token` header, which is the
 * double-submit pattern the backend enforces in production.
 */
export function getCsrfToken(): string | undefined {
  if (typeof document === 'undefined') return undefined;
  const match = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]*)/);
  const token = match?.[1];
  return token ? decodeURIComponent(token) : undefined;
}

export function buildAuthHeaders(): Record<string, string> {
  const headers: Record<string, string> = {};

  const userEmail = getUserEmail();
  if (userEmail) headers['X-User-Email'] = userEmail;

  // The CSRF double-submit: the backend compares this header with the
  // csrf_token cookie it set at sign-in. Without the header, a deployment
  // that runs with ENVIRONMENT=production answers every state-changing
  // request with 403 - the login, the search, the chat.
  const csrfToken = getCsrfToken();
  if (csrfToken) headers['X-CSRF-Token'] = csrfToken;

  return headers;
}

export function buildHeaders(extra?: Record<string, string>): Record<string, string> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  return { ...headers, ...buildAuthHeaders(), ...(extra || {}) };
}

export function buildMultipartHeaders(extra?: Record<string, string>): Record<string, string> {
  return { ...buildAuthHeaders(), ...(extra || {}) };
}

/**
 * Safely perform a fetch request with network error handling.
 * Wraps fetch to convert network failures into ApiError.
 */
export async function safeFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(input, init);
  } catch (error) {
    // Network errors (offline, DNS, CORS, etc.)
    throw ApiError.networkError(error instanceof Error ? error : undefined);
  }
}

export async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const errorText = await response.text().catch(() => '');
    const headers = (response as unknown as { headers?: { get?: (name: string) => string | null } })
      .headers;
    const requestId =
      headers && typeof headers.get === 'function'
        ? headers.get('X-Request-ID') || undefined
        : undefined;
    let message = 'API request failed';
    if (errorText) {
      try {
        const parsed: unknown = JSON.parse(errorText);
        if (parsed && typeof parsed === 'object') {
          const detail = (parsed as { detail?: unknown }).detail;
          if (typeof detail === 'string' && detail.trim()) {
            message = detail.trim();
          } else if (detail !== undefined) {
            message = JSON.stringify(detail);
          } else {
            message = errorText;
          }
        } else {
          message = errorText;
        }
      } catch {
        message = errorText;
      }
    }
    throw new ApiError(message, response.status, requestId || undefined);
  }
  return response.json();
}
