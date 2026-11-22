/**
 * The request layer.
 *
 * One place knows how to talk to the API: the base URL, the key header, the
 * JSON in and the JSON out. The commands above it only describe what they
 * ask for.
 *
 * The key is written into the request headers and nowhere else. It is not
 * logged, not put in the error message and not put in the URL - a URL ends
 * up in access logs, and an access log is a place a key should not be.
 */

import type { ApiConfig } from './config.js';

/** The server answered something the client cannot use. */
export class ApiError extends Error {
  /** The status the server answered with. */
  readonly status: number;
  /** The body the server answered with, truncated. */
  readonly detail: string;

  constructor(status: number, detail: string) {
    super(`The API answered ${status}${detail ? `: ${detail}` : ''}`);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

/** The client could not reach the server at all. */
export class NetworkError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'NetworkError';
  }
}

/** The longest body an error message carries. */
const MAX_DETAIL = 400;

export type FetchLike = (input: string, init?: RequestInit) => Promise<Response>;

export class ApiClient {
  private readonly config: ApiConfig;
  private readonly fetchImpl: FetchLike;

  constructor(config: ApiConfig, fetchImpl: FetchLike = fetch) {
    this.config = config;
    this.fetchImpl = fetchImpl;
  }

  /** The absolute address of a path below the API root. */
  url(path: string): string {
    const base = this.config.baseUrl.replace(/\/+$/, '');
    const suffix = path.startsWith('/') ? path : `/${path}`;
    return `${base}${suffix}`;
  }

  /** A GET below the API root. */
  async get<T>(path: string): Promise<T> {
    return this.request<T>(path, 'get');
  }

  /** A POST below the API root. */
  async post<T>(path: string, body: unknown): Promise<T> {
    return this.request<T>(path, 'post', body);
  }

  private async request<T>(path: string, method: 'get' | 'post', body?: unknown): Promise<T> {
    const headers: Record<string, string> = {
      Accept: 'application/json',
      'X-API-Key': this.config.apiKey,
    };
    const init: RequestInit = { method: method.toUpperCase(), headers };

    if (body !== undefined) {
      headers['Content-Type'] = 'application/json';
      init.body = JSON.stringify(body);
    }

    let response: Response;
    try {
      response = await this.fetchImpl(this.url(path), init);
    } catch (error) {
      const reason = error instanceof Error ? error.message : String(error);
      throw new NetworkError(`The API at ${this.config.baseUrl} did not answer: ${reason}`);
    }

    const text = await response.text();
    if (!response.ok) {
      throw new ApiError(response.status, text.slice(0, MAX_DETAIL));
    }
    if (!text) {
      return undefined as T;
    }
    try {
      return JSON.parse(text) as T;
    } catch {
      throw new ApiError(response.status, `the answer was not JSON: ${text.slice(0, MAX_DETAIL)}`);
    }
  }
}
