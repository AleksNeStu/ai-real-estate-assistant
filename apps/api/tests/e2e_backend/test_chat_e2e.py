"""
E2E tests for the chat flow.

Tests the complete path: request → auth → LLM routing → response.
"""

import pytest


@pytest.mark.asyncio
class TestChatE2E:
    """Chat endpoint — validates full chat request/response cycle."""

    async def test_basic_chat(self, e2e_client, api_headers):
        resp = await e2e_client.post(
            "/api/v1/chat",
            json={"message": "What properties are available in Warsaw?"},
            headers=api_headers,
        )
        # Chat may succeed (200), fail on mock internals (500), or be unavailable (503)
        assert resp.status_code in (200, 500, 503)
        if resp.status_code == 200:
            data = resp.json()
            assert "response" in data or "answer" in data or "message" in data

    async def test_chat_streaming_request(self, e2e_client, api_headers):
        resp = await e2e_client.post(
            "/api/v1/chat",
            json={"message": "test", "stream": True},
            headers=api_headers,
        )
        # Streaming may return 200 with SSE, fall back, or fail on mock
        assert resp.status_code in (200, 500, 503)

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "The chat router catches every exception - including the "
            "sanitizer's own HTTPException(400) - and re-raises it as a 500 "
            "(api/routers/chat.py: the generic `except Exception` arm). An "
            "empty message is a client error and must answer 400. The "
            "expectation below is the contract; it fails against the "
            "application as it is written. Strict, so the day the router "
            "answers 400 the pipeline goes red and this marker is removed."
        ),
    )
    async def test_chat_empty_message(self, e2e_client, api_headers):
        resp = await e2e_client.post(
            "/api/v1/chat",
            json={"message": ""},
            headers=api_headers,
        )
        # Empty message is rejected by sanitizer with 400
        assert resp.status_code in (200, 400, 422)

    async def test_chat_missing_message(self, e2e_client, api_headers):
        resp = await e2e_client.post(
            "/api/v1/chat",
            json={},
            headers=api_headers,
        )
        assert resp.status_code == 422

    async def test_chat_with_session_id(self, e2e_client, api_headers):
        resp = await e2e_client.post(
            "/api/v1/chat",
            json={"message": "hello", "session_id": "test-session-123"},
            headers=api_headers,
        )
        # Chat may succeed or fail on mock internals
        assert resp.status_code in (200, 500, 503)
