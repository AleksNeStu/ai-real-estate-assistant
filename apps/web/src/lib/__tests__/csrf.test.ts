import { buildHeaders, getCsrfToken } from '@/lib/api/client';

/**
 * The CSRF double-submit, browser side.
 *
 * The backend compares the `X-CSRF-Token` header with the `csrf_token`
 * cookie it set at sign-in, and it enforces that in production. The browser
 * has to read the cookie and send it back - without the header, every
 * state-changing request in a production deployment answers 403.
 */

describe('the CSRF token in the browser', () => {
  afterEach(() => {
    for (const cookie of document.cookie.split(';')) {
      const name = cookie.split('=')[0]?.trim();
      if (name) document.cookie = `${name}=; Max-Age=0; path=/`;
    }
  });

  it('reads the token out of the cookie', () => {
    document.cookie = 'csrf_token=token-value; path=/';
    expect(getCsrfToken()).toBe('token-value');
  });

  it('has no token before the visitor signs in', () => {
    expect(getCsrfToken()).toBeUndefined();
  });

  it('does not confuse another cookie for the token', () => {
    document.cookie = 'access_token=session; path=/';
    expect(getCsrfToken()).toBeUndefined();
  });

  it('sends the token back with every request', () => {
    document.cookie = 'csrf_token=token-value; path=/';
    const headers = buildHeaders();
    expect(headers['X-CSRF-Token']).toBe('token-value');
  });

  it('sends no header when there is no token', () => {
    const headers = buildHeaders();
    expect(headers['X-CSRF-Token']).toBeUndefined();
  });
});
