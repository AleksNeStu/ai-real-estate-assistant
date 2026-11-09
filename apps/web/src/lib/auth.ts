/**
 * Authentication API client for the AI Real Estate Assistant.
 *
 * This module provides functions for interacting with the backend authentication endpoints.
 * The backend uses httpOnly cookies for token storage, so tokens are automatically handled
 * by the browser.
 */

import { ApiError } from './api';

// Auth types matching backend schemas

export interface User {
  id: string;
  email: string;
  full_name?: string | null;
  is_active: boolean;
  is_verified: boolean;
  role: string;
  created_at: string;
  last_login_at?: string | null;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name?: string;
}

export interface PasswordResetRequest {
  email: string;
}

export interface PasswordResetConfirm {
  token: string;
  new_password: string;
}

export interface EmailVerificationRequest {
  token: string;
}

export interface MessageResponse {
  message: string;
  detail?: string;
}

/**
 * Get the base API URL for authentication endpoints.
 */
function getAuthApiUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL || '/api/v1';
}

/**
 * Build headers for auth requests.
 */
function buildAuthHeaders(): Record<string, string> {
  return {
    'Content-Type': 'application/json',
  };
}

/**
 * Handle API response with proper error handling.
 */
async function handleAuthResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const errorText = await response.text().catch(() => '');
    const requestId = response.headers.get('X-Request-ID') || undefined;
    let message = 'Authentication request failed';

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

/**
 * Login with email and password.
 *
 * @param email - User email
 * @param password - User password
 * @returns AuthResponse with user info and tokens
 */
export async function login(email: string, password: string): Promise<AuthResponse> {
  const response = await fetch(`${getAuthApiUrl()}/auth/login`, {
    method: 'POST',
    headers: buildAuthHeaders(),
    body: JSON.stringify({ email, password }),
    credentials: 'include',
  });

  return handleAuthResponse<AuthResponse>(response);
}

/**
 * Register a new user account.
 *
 * @param email - User email
 * @param password - User password (min 8 chars, must contain uppercase, lowercase, and digit)
 * @param fullName - User's full name (optional)
 * @param consentGiven - The visitor ticked the consent box. The backend
 *   writes `gdpr_consent_at` from it, so it has to travel with the request:
 *   without it the account is created with no record of the consent.
 * @returns AuthResponse with user info and tokens
 */
export async function register(
  email: string,
  password: string,
  fullName?: string,
  consentGiven = false
): Promise<AuthResponse> {
  const response = await fetch(`${getAuthApiUrl()}/auth/register`, {
    method: 'POST',
    headers: buildAuthHeaders(),
    body: JSON.stringify({
      email,
      password,
      full_name: fullName,
      consent_given: consentGiven,
    }),
    credentials: 'include',
  });

  return handleAuthResponse<AuthResponse>(response);
}

/**
 * Logout the current user.
 *
 * This invalidates the refresh token and clears auth cookies.
 */
export async function logout(): Promise<MessageResponse> {
  const response = await fetch(`${getAuthApiUrl()}/auth/logout`, {
    method: 'POST',
    headers: buildAuthHeaders(),
    credentials: 'include',
  });

  return handleAuthResponse<MessageResponse>(response);
}

/**
 * Refresh the access token using the refresh token cookie.
 *
 * This is typically called automatically when a 401 error is received.
 * The refresh token must be stored in an httpOnly cookie.
 *
 * @returns AuthResponse with new tokens
 */
export async function refreshToken(): Promise<AuthResponse> {
  const response = await fetch(`${getAuthApiUrl()}/auth/refresh`, {
    method: 'POST',
    headers: buildAuthHeaders(),
    credentials: 'include',
  });

  return handleAuthResponse<AuthResponse>(response);
}

/**
 * Get the currently authenticated user's profile.
 * Fails silently (no console error) for expected 401/404 responses.
 *
 * @returns User object
 */
export async function getCurrentUser(): Promise<User> {
  const response = await fetch(`${getAuthApiUrl()}/auth/me`, {
    method: 'GET',
    headers: buildAuthHeaders(),
    credentials: 'include',
  });

  if (!response.ok) {
    const errorText = await response.text().catch(() => '');
    let message = 'Not authenticated';

    if (errorText) {
      try {
        const parsed: unknown = JSON.parse(errorText);
        if (parsed && typeof parsed === 'object') {
          const detail = (parsed as { detail?: unknown }).detail;
          if (typeof detail === 'string' && detail.trim()) {
            message = detail.trim();
          }
        }
      } catch {
        // ignore parse errors
      }
    }

    throw new ApiError(message, response.status);
  }

  return response.json();
}

/**
 * Request a password reset email.
 *
 * @param email - User email address
 * @returns Message confirming email was sent (or not revealing if user exists)
 */
export async function forgotPassword(email: string): Promise<MessageResponse> {
  const response = await fetch(`${getAuthApiUrl()}/auth/forgot-password`, {
    method: 'POST',
    headers: buildAuthHeaders(),
    body: JSON.stringify({ email }),
    credentials: 'include',
  });

  return handleAuthResponse<MessageResponse>(response);
}

/**
 * Reset password using a token from the email.
 *
 * @param token - Password reset token from email
 * @param newPassword - New password (min 8 chars, must contain uppercase, lowercase, and digit)
 * @returns Message confirming password was reset
 */
export async function resetPassword(token: string, newPassword: string): Promise<MessageResponse> {
  const response = await fetch(`${getAuthApiUrl()}/auth/reset-password`, {
    method: 'POST',
    headers: buildAuthHeaders(),
    body: JSON.stringify({
      token,
      new_password: newPassword,
    }),
    credentials: 'include',
  });

  return handleAuthResponse<MessageResponse>(response);
}

/**
 * Verify email address using a token from the verification email.
 *
 * @param token - Email verification token
 * @returns Message confirming email was verified
 */
export async function verifyEmail(token: string): Promise<MessageResponse> {
  const response = await fetch(`${getAuthApiUrl()}/auth/verify-email`, {
    method: 'POST',
    headers: buildAuthHeaders(),
    body: JSON.stringify({ token }),
    credentials: 'include',
  });

  return handleAuthResponse<MessageResponse>(response);
}

/**
 * Resend email verification token.
 *
 * @param email - User email address
 * @returns Message confirming email was sent (or not revealing if user exists)
 */
export async function resendVerificationEmail(email: string): Promise<MessageResponse> {
  const response = await fetch(`${getAuthApiUrl()}/auth/resend-verification`, {
    method: 'POST',
    headers: buildAuthHeaders(),
    body: JSON.stringify({ email }),
    credentials: 'include',
  });

  return handleAuthResponse<MessageResponse>(response);
}

/**
 * Initiate OAuth login flow.
 *
 * This redirects the browser to the OAuth provider's authorization page.
 * Currently supports 'google' and 'apple' (though Apple requires backend setup).
 *
 * @param provider - OAuth provider ('google' | 'apple')
 * @throws Error if OAuth is not configured or request fails
 */
export async function oauthLogin(provider: 'google' | 'apple'): Promise<void> {
  const baseUrl = getAuthApiUrl();
  const authUrl = `${baseUrl}/auth/oauth/${provider}`;

  const response = await fetch(authUrl, {
    method: 'GET',
    headers: buildAuthHeaders(),
    credentials: 'include',
  });

  if (!response.ok) {
    let detail = 'Failed to initiate OAuth flow';
    try {
      const body: unknown = await response.json();
      if (body && typeof body === 'object' && 'detail' in body) {
        const d = (body as { detail?: unknown }).detail;
        if (typeof d === 'string') detail = d;
      }
    } catch {
      // ignore parse errors
    }
    throw new Error(detail);
  }

  const data = await response.json();
  if (data.authorization_url) {
    window.location.href = data.authorization_url;
  } else {
    throw new Error('Invalid OAuth response');
  }
}

/**
 * Check if user is authenticated by fetching current user.
 *
 * This is a lightweight check that returns the user if authenticated,
 * or throws an error if not.
 *
 * @returns User object if authenticated
 * @throws ApiError if not authenticated
 */
export async function checkAuth(): Promise<User> {
  return getCurrentUser();
}
