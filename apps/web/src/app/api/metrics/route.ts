/**
 * Proxy for /metrics endpoint (Task #57)
 * Prometheus metrics endpoint (text/plain).
 */

import { NextRequest, NextResponse } from 'next/server';

import { getApiAccessKey, getBackendApiBaseUrl } from '@/lib/proxy-utils';

export async function GET(_request: NextRequest) {
  // The same base the other monitoring routes use - the deployment names it
  // BACKEND_API_URL, and the old BACKEND_URL default pointed at the
  // frontend's own port.
  const backendUrl = getBackendApiBaseUrl().replace(/\/api\/v1\/?$/, '');
  const url = `${backendUrl}/metrics`;

  const headers = new Headers();
  const apiKey = getApiAccessKey();
  if (apiKey) {
    headers.set('X-API-Key', apiKey);
  }

  const response = await fetch(url, { headers });

  const text = await response.text();
  return new NextResponse(text, {
    status: response.status,
    headers: {
      'Content-Type': 'text/plain',
    },
  });
}
