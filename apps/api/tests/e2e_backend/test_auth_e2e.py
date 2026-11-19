"""
E2E tests for authentication flows.
"""

import pytest


@pytest.mark.asyncio
class TestAuthE2E:
    """API key authentication — validates auth middleware rejects bad keys."""

    async def test_search_requires_api_key(self, e2e_client, requires_api_key):
        resp = await e2e_client.post("/api/v1/search", json={"query": "test"})
        assert resp.status_code == 401

    async def test_search_rejects_invalid_api_key(self, e2e_client, requires_api_key):
        resp = await e2e_client.post(
            "/api/v1/search",
            json={"query": "test"},
            headers={"X-API-Key": "invalid-key"},
        )
        assert resp.status_code in (401, 403)

    async def test_search_accepts_valid_api_key(self, e2e_client, api_headers):
        resp = await e2e_client.post(
            "/api/v1/search",
            json={"query": "apartments in Krakow"},
            headers=api_headers,
        )
        assert resp.status_code == 200

    async def test_chat_requires_api_key(self, e2e_client, requires_api_key):
        resp = await e2e_client.post("/api/v1/chat", json={"message": "hello"})
        assert resp.status_code == 401

    async def test_rag_requires_api_key(self, e2e_client, requires_api_key):
        resp = await e2e_client.post("/api/v1/rag/qa", json={"question": "test"})
        assert resp.status_code == 401

    async def test_admin_requires_api_key(self, e2e_client, requires_api_key):
        resp = await e2e_client.post("/api/v1/admin/ingest")
        assert resp.status_code == 401

    async def test_auth_endpoint_no_key_needed(self, e2e_client):
        """Auth endpoints should be accessible without API key."""
        resp = await e2e_client.post(
            "/api/v1/auth/request-code",
            json={"email": "test@example.com"},
        )
        # May return 4xx for invalid input, but NOT 401
        assert resp.status_code != 401

    async def test_metrics_no_key_needed(self, e2e_client):
        """Metrics endpoint should be accessible without API key."""
        resp = await e2e_client.get("/metrics")
        assert resp.status_code == 200
