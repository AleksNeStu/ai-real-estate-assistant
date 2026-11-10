/**
 * Proxy for /monitoring/test-alert endpoint (Task #57)
 * Test alert endpoint for monitoring notifications.
 */

import { NextRequest, NextResponse } from 'next/server';

import { getApiAccessKey, getBackendApiBaseUrl } from '@/lib/proxy-utils';

export async function POST(request: NextRequest) {
  // The same base the other monitoring routes use - the deployment names it
  // BACKEND_API_URL, and the old BACKEND_URL default pointed at the
  // frontend's own port.
  const backendUrl = getBackendApiBaseUrl().replace(/\/api\/v1\/?$/, '');
  const url = `${backendUrl}/monitoring/test-alert`;

  const headers = new Headers();
  const apiKey = getApiAccessKey();
  if (apiKey) {
    headers.set('X-API-Key', apiKey);
  }
  // Sending a test alert is an administrator's action, so the session cookie
  // travels with the request.
  const cookie = request.headers.get('cookie');
  if (cookie) {
    headers.set('cookie', cookie);
  }

  const response = await fetch(url, {
    method: 'POST',
    headers,
  });

  const data = await response.json();
  return NextResponse.json(data, { status: response.status });
}
