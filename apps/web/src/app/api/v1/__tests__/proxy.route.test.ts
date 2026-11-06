import { DELETE, GET, OPTIONS, PATCH, POST, PUT } from "../[...path]/route";

function makeRequest(options: {
  url: string;
  method: string;
  headers?: Record<string, string>;
  body?: unknown;
}): Request {
  return {
    url: options.url,
    method: options.method,
    headers: new Headers(options.headers ?? {}),
    body: options.body ?? null,
  } as unknown as Request;
}

describe("API v1 proxy route", () => {
  beforeEach(() => {
    jest.resetAllMocks();
    (global.fetch as unknown as jest.Mock) = jest.fn();
    process.env.BACKEND_API_URL = "http://backend:8000/api/v1";
    process.env.API_ACCESS_KEY = "server-secret-key";
    delete process.env.API_ACCESS_KEYS;
  });

  afterEach(() => {
    delete process.env.BACKEND_API_URL;
    delete process.env.API_ACCESS_KEY;
    delete process.env.API_ACCESS_KEYS;
  });

  it("forwards requests to backend and injects X-API-Key server-side", async () => {
    (global.fetch as unknown as jest.Mock).mockResolvedValueOnce(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: {
          "Content-Type": "application/json",
          "X-Request-ID": "req-1",
        },
      })
    );

    const request = makeRequest({
      url: "http://localhost/api/v1/search?foo=1",
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-User-Email": "user@example.com",
        "X-API-Key": "malicious-client-key",
      },
    });

    const response = await POST(request, { params: Promise.resolve({ path: ["search"] }) });

    expect(global.fetch).toHaveBeenCalledTimes(1);
    const [backendUrl, init] = (global.fetch as unknown as jest.Mock).mock.calls[0] as [
      string,
      RequestInit & { headers?: Headers },
    ];

    expect(backendUrl).toBe("http://backend:8000/api/v1/search?foo=1");
    expect(init.method).toBe("POST");

    const headers = init.headers as Headers;
    expect(headers.get("X-API-Key")).toBe("server-secret-key");
    expect(headers.get("X-User-Email")).toBe("user@example.com");
    expect(headers.get("Content-Type")).toBe("application/json");

    expect(response.status).toBe(200);
    expect(response.headers.get("X-Request-ID")).toBe("req-1");
  });

  it("forwards the session cookie and authorization header, but overrides client-supplied X-API-Key", async () => {
    (global.fetch as unknown as jest.Mock).mockResolvedValueOnce(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: {
          "Content-Type": "application/json",
        },
      })
    );

    const request = makeRequest({
      url: "http://localhost/api/v1/settings/notifications",
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Cookie: "access_token=jwt-token",
        Authorization: "Bearer jwt-token",
        "X-API-Key": "malicious-client-key",
      },
    });

    await POST(request, { params: Promise.resolve({ path: ["settings", "notifications"] }) });

    const [, init] = (global.fetch as unknown as jest.Mock).mock.calls[0] as [string, RequestInit & { headers?: Headers }];
    const headers = init.headers as Headers;
    // The backend reads the session from the access_token cookie or the
    // Authorization header — without them every authenticated surface 401s.
    expect(headers.get("cookie")).toBe("access_token=jwt-token");
    expect(headers.get("authorization")).toBe("Bearer jwt-token");
    expect(headers.get("X-API-Key")).toBe("server-secret-key");
  });

  it("supports empty path and omits X-API-Key when no access key env is set", async () => {
    delete process.env.API_ACCESS_KEY;
    delete process.env.API_ACCESS_KEYS;

    (global.fetch as unknown as jest.Mock).mockResolvedValueOnce(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: {
          "Content-Type": "application/json",
        },
      })
    );

    const request = makeRequest({
      url: "http://localhost/api/v1?x=1",
      method: "GET",
      headers: {
        Accept: "application/json",
      },
    });

    await GET(request, { params: Promise.resolve({ path: [] }) });

    const [backendUrl, init] = (global.fetch as unknown as jest.Mock).mock.calls[0] as [
      string,
      RequestInit & { headers?: Headers; body?: unknown },
    ];
    expect(backendUrl).toBe("http://backend:8000/api/v1?x=1");

    const headers = init.headers as Headers;
    expect(headers.get("X-API-Key")).toBeNull();
    expect(init.body).toBeUndefined();
  });

  it("falls back to API_ACCESS_KEYS when API_ACCESS_KEY is missing", async () => {
    delete process.env.API_ACCESS_KEY;
    process.env.API_ACCESS_KEYS = " rotated-key-1 , rotated-key-2 ";

    (global.fetch as unknown as jest.Mock).mockResolvedValueOnce(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: {
          "Content-Type": "application/json",
        },
      })
    );

    const request = makeRequest({
      url: "http://localhost/api/v1/verify-auth",
      method: "GET",
      headers: {
        Accept: "application/json",
      },
    });

    await GET(request, { params: Promise.resolve({ path: ["verify-auth"] }) });

    const [, init] = (global.fetch as unknown as jest.Mock).mock.calls[0] as [
      string,
      RequestInit & { headers?: Headers },
    ];
    const headers = init.headers as Headers;
    expect(headers.get("X-API-Key")).toBe("rotated-key-1");
  });

  it("exposes method wrappers for PUT/PATCH/DELETE/OPTIONS", async () => {
    (global.fetch as unknown as jest.Mock).mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: {
          "Content-Type": "application/json",
        },
      })
    );

    const makeMethodRequest = (method: string) =>
      makeRequest({
        url: "http://localhost/api/v1/tools/mortgage-calculator",
        method,
        headers: { "Content-Type": "application/json" },
      });

    const params = Promise.resolve({ path: ["tools", "mortgage-calculator"] });
    await PUT(makeMethodRequest("PUT"), { params });
    await PATCH(makeMethodRequest("PATCH"), { params });
    await DELETE(makeMethodRequest("DELETE"), { params });
    await OPTIONS(makeMethodRequest("OPTIONS"), { params });

    expect(global.fetch).toHaveBeenCalledTimes(4);
  });

  it("returns 500 when BACKEND_API_URL is missing in production", async () => {
    const originalNodeEnv = process.env.NODE_ENV;
    process.env.NODE_ENV = "production";
    delete process.env.BACKEND_API_URL;

    const request = makeRequest({
      url: "http://localhost/api/v1/search",
      method: "GET",
      headers: {
        Accept: "application/json",
      },
    });

    const response = await GET(request, { params: Promise.resolve({ path: ["search"] }) });

    expect(response.status).toBe(500);
    const payload = (await response.json()) as { detail?: unknown };
    expect(payload.detail).toBe("BACKEND_API_URL must be set in production");
    expect(global.fetch).not.toHaveBeenCalled();

    process.env.NODE_ENV = originalNodeEnv;
  });

  it("returns 500 when BACKEND_API_URL points to localhost in production", async () => {
    const originalNodeEnv = process.env.NODE_ENV;
    process.env.NODE_ENV = "production";
    process.env.BACKEND_API_URL = "http://localhost:8000/api/v1";

    const request = makeRequest({
      url: "http://localhost/api/v1/search",
      method: "GET",
      headers: {
        Accept: "application/json",
      },
    });

    const response = await GET(request, { params: Promise.resolve({ path: ["search"] }) });

    expect(response.status).toBe(500);
    const payload = (await response.json()) as { detail?: unknown };
    expect(payload.detail).toBe("BACKEND_API_URL must not point to localhost in production");
    expect(global.fetch).not.toHaveBeenCalled();

    process.env.NODE_ENV = originalNodeEnv;
  });
});
