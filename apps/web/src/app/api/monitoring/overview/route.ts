import { NextRequest } from 'next/server';
import { getBackendApiBaseUrl, getApiAccessKey, filterResponseHeaders } from '@/lib/proxy-utils';

export const runtime = 'nodejs';

async function proxyRequest(request: NextRequest): Promise<Response> {
  const baseUrl = getBackendApiBaseUrl().replace(/\/api\/v1\/?$/, '');
  const targetUrl = `${baseUrl}/monitoring/overview`;

  const headers = new Headers();
  const apiKey = getApiAccessKey();
  if (apiKey) {
    headers.set('X-API-Key', apiKey);
  }
  // The overview answers for a signed-in account, so the session cookie
  // travels with the request.
  const cookie = request.headers.get('cookie');
  if (cookie) {
    headers.set('cookie', cookie);
  }

  try {
    const response = await fetch(targetUrl, { method: 'GET', headers });

    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: filterResponseHeaders(response.headers),
    });
  } catch (error) {
    return new Response(
      JSON.stringify({
        detail: 'Backend monitoring overview unavailable',
        error: error instanceof Error ? error.message : 'Unknown error',
      }),
      {
        status: 502,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}

export async function GET(request: NextRequest): Promise<Response> {
  return proxyRequest(request);
}
