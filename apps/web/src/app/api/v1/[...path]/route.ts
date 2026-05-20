import type { NextRequest } from 'next/server';

export const runtime = 'nodejs';

type ProxyContext = {
  params: Promise<{
    path: string[];
  }>;
};

const HOP_BY_HOP_RESPONSE_HEADERS = new Set<string>([
  'connection',
  'keep-alive',
  'proxy-authenticate',
  'proxy-authorization',
  'te',
  'trailer',
  'transfer-encoding',
  'upgrade',
]);

const FORWARDED_REQUEST_HEADERS = [
  'accept',
  'accept-language',
  'content-type',
  'user-agent',
  'x-user-email',
  'x-request-id',
] as const;

function isProductionRuntime(): boolean {
  if (process.env.NODE_ENV === 'production') return true;
  if (process.env.VERCEL_ENV === 'production') return true;
  if (process.env.VERCEL === '1') return true;
  return false;
}

function isLocalhostUrl(value: string): boolean {
  const trimmed = value.trim().toLowerCase();
  return (
    trimmed.includes('://localhost') ||
    trimmed.includes('://127.0.0.1') ||
    trimmed.includes('://[::1]') ||
    trimmed.includes('://0.0.0.0')
  );
}

function getBackendApiBaseUrl(): string {
  const raw = process.env.BACKEND_API_URL;
  if (isProductionRuntime()) {
    const trimmed = raw?.trim();
    if (!trimmed) {
      throw new Error('BACKEND_API_URL must be set in production');
    }
    if (isLocalhostUrl(trimmed)) {
      throw new Error('BACKEND_API_URL must not point to localhost in production');
    }
  }

  // Use BACKEND_API_URL env var with dynamic port support
  const defaultBackendUrl =
    process.env.BACKEND_API_URL ||
    (process.env.BACKEND_PORT
      ? `http://localhost:${process.env.BACKEND_PORT}/api/v1`
      : 'http://localhost:8000/api/v1');
  const fallback = raw || defaultBackendUrl;
  return fallback.replace(/\/+$/, '');
}

function getApiAccessKey(): string | undefined {
  const raw = process.env.API_ACCESS_KEY;
  if (raw) {
    const trimmed = raw.trim();
    if (trimmed) return trimmed;
  }

  const rotated = process.env.API_ACCESS_KEYS;
  if (!rotated) return undefined;
  const first = rotated
    .split(',')
    .map((value) => value.trim())
    .find((value) => Boolean(value));
  return first ? first : undefined;
}

function buildBackendUrl(requestUrl: URL, pathParts: string[]): string {
  const base = getBackendApiBaseUrl();
  const encodedPath = pathParts.map((part) => encodeURIComponent(part)).join('/');
  const joined = encodedPath ? `${base}/${encodedPath}` : base;
  const target = new URL(joined);
  target.search = requestUrl.search;
  return target.toString();
}

function buildBackendRequestHeaders(original: Headers): Headers {
  const headers = new Headers();

  for (const headerName of FORWARDED_REQUEST_HEADERS) {
    const value = original.get(headerName);
    if (value) headers.set(headerName, value);
  }

  const apiKey = getApiAccessKey();
  if (apiKey) headers.set('X-API-Key', apiKey);

  // Prevent backend gzip compression — the proxy streams raw bytes to the
  // browser, so decompressing gzip in the browser would require forwarding
  // the Content-Encoding header. Requesting identity avoids the issue.
  headers.set('Accept-Encoding', 'identity');

  return headers;
}

async function proxyRequest(request: Request, context: ProxyContext): Promise<Response> {
  const requestUrl = new URL(request.url);
  const { path } = await context.params;
  const pathParts = path ?? [];

  const body = request.method === 'GET' || request.method === 'HEAD' ? undefined : request.body;

  const init: RequestInit & { duplex?: 'half' } = {
    method: request.method,
    headers: buildBackendRequestHeaders(request.headers),
    body,
    redirect: 'manual',
  };
  if (body) init.duplex = 'half';

  let backendUrl: string;
  try {
    backendUrl = buildBackendUrl(requestUrl, pathParts);
  } catch (error) {
    const message =
      error instanceof Error && error.message.trim()
        ? error.message.trim()
        : 'Proxy configuration error';
    return new Response(JSON.stringify({ detail: message }), {
      status: 500,
      headers: {
        'Content-Type': 'application/json',
        'Cache-Control': 'no-store',
      },
    });
  }

  const backendResponse = await fetch(backendUrl, init);

  const responseHeaders = new Headers();
  for (const [name, value] of backendResponse.headers.entries()) {
    if (HOP_BY_HOP_RESPONSE_HEADERS.has(name.toLowerCase())) continue;
    responseHeaders.set(name, value);
  }

  return new Response(backendResponse.body, {
    status: backendResponse.status,
    statusText: backendResponse.statusText,
    headers: responseHeaders,
  });
}

export async function GET(request: NextRequest, context: ProxyContext): Promise<Response> {
  return proxyRequest(request, context);
}

export async function POST(request: NextRequest, context: ProxyContext): Promise<Response> {
  return proxyRequest(request, context);
}

export async function PUT(request: NextRequest, context: ProxyContext): Promise<Response> {
  return proxyRequest(request, context);
}

export async function PATCH(request: NextRequest, context: ProxyContext): Promise<Response> {
  return proxyRequest(request, context);
}

export async function DELETE(request: NextRequest, context: ProxyContext): Promise<Response> {
  return proxyRequest(request, context);
}

export async function OPTIONS(request: NextRequest, context: ProxyContext): Promise<Response> {
  return proxyRequest(request, context);
}
