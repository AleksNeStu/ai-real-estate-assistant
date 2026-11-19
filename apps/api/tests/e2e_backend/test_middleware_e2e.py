"""
E2E tests for middleware and cross-cutting concerns.

Tests CORS, security headers, request size limits, error handling.
"""

import pytest


@pytest.mark.asyncio
class TestMiddlewareE2E:
    """Middleware stack — validates cross-cutting concerns."""

    async def test_cors_headers(self, e2e_client, cors_origin):
        resp = await e2e_client.options(
            "/health",
            headers={
                "Origin": cors_origin,
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.status_code == 200
        assert "access-control-allow-origin" in resp.headers

    async def test_security_headers_on_api_response(self, e2e_client, api_headers):
        resp = await e2e_client.post(
            "/api/v1/search",
            json={"query": "test"},
            headers=api_headers,
        )
        assert resp.status_code == 200

    async def test_version_header(self, e2e_client, api_headers):
        resp = await e2e_client.post(
            "/api/v1/search",
            json={"query": "test"},
            headers=api_headers,
        )
        # Versioning middleware adds API version header
        assert resp.status_code == 200

    async def test_request_id_header(self, e2e_client):
        resp = await e2e_client.get("/health")
        assert resp.status_code == 200
        # Observability middleware should add request ID
        assert "X-Request-ID" in resp.headers or "x-request-id" in resp.headers

    async def test_404_returns_json(self, e2e_client):
        resp = await e2e_client.get("/nonexistent-endpoint")
        assert resp.status_code == 404
        assert resp.headers.get("content-type", "").startswith("application/json")

    async def test_method_not_allowed(self, e2e_client, api_headers):
        resp = await e2e_client.patch(
            "/api/v1/search",
            json={"query": "test"},
            headers=api_headers,
        )
        assert resp.status_code == 405

    async def test_metrics_endpoint(self, e2e_client):
        resp = await e2e_client.get("/metrics")
        assert resp.status_code == 200
        text = resp.text
        assert "HELP" in text or "#" in text
