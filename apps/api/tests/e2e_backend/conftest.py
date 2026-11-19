"""
E2E test fixtures — full app lifecycle with real dependency wiring.

These tests exercise the complete request path:
  Client → Auth Middleware → Router → Service → Response

Two modes, and the mode is chosen by the environment:

* **in-process** (the default) — the real FastAPI application over ASGI, with
  the LLM and the vector store replaced by mocks. No server has to run, and no
  database has to be seeded. This is how the suite runs while the product is
  being written.

* **against a running backend** — set ``E2E_BASE_URL`` and the suite talks to
  a real server over HTTP. The pipeline runs it this way against the compose
  stack, so the assertions are made against the product as it is deployed:
  the real middleware stack, the real catalogue, the real provider (the local
  MockLLM — no paid key, no answer leaves the runner).

The two modes have to agree, or the suite only proves one of them.
"""

import os
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

# Ensure test environment before any app imports
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("API_ACCESS_KEY", "test-e2e-key-12345")
os.environ.setdefault("ENABLE_JWT_AUTH", "false")

# The key the suite authenticates with. Against a running backend the key is
# the server's own key, so it can be named explicitly; in-process it is the
# key the application under test was configured with.
API_KEY = os.environ.get("E2E_API_KEY") or os.environ["API_ACCESS_KEY"]

# The base URL of a running backend. Empty means "in-process".
E2E_BASE_URL = os.environ.get("E2E_BASE_URL", "").strip()

# The origin the CORS assertions send. It has to be an origin the server
# allows - the compose stack allows the two origins it is served on, not the
# development one, so the pipeline names it.
E2E_CORS_ORIGIN = os.environ.get("E2E_CORS_ORIGIN", "http://localhost:3000")


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def e2e_client() -> AsyncGenerator[AsyncClient, None]:
    """
    The client the suite talks to.

    The scope is a function, not a session: a live client pools its
    connections, and a session-scoped pool is torn down on an event loop
    that the test runner has already closed - which fails the teardown of
    every test that used it.

    Overrides only external services (LLM, vector store) to avoid
    hitting real APIs while keeping auth, middleware, and routing intact.
    """
    if E2E_BASE_URL:
        # A running backend: the application under test is the deployed one,
        # so nothing here is overridden - the point is to test it as it is.
        async with AsyncClient(base_url=E2E_BASE_URL, timeout=60.0) as client:
            yield client
        return

    from unittest.mock import AsyncMock, MagicMock

    from api.dependencies import get_llm, get_optional_llm_with_details, get_vector_store
    from api.main import app

    # Mock vector store
    mock_store = MagicMock()
    mock_store.similarity_search_with_score.return_value = []
    mock_store.get_stats.return_value = {"documents": 0}

    # Mock LLM
    mock_llm = MagicMock()
    mock_msg = MagicMock()
    mock_msg.content = "E2E test response"
    mock_llm.invoke.return_value = mock_msg
    mock_llm.astream = AsyncMock()

    app.dependency_overrides[get_vector_store] = lambda: mock_store
    app.dependency_overrides[get_llm] = lambda: mock_llm
    app.dependency_overrides[get_optional_llm_with_details] = lambda: (
        mock_llm,
        "mock",
        "mock-model",
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def api_headers() -> dict[str, str]:
    """Headers with valid API key."""
    return {"X-API-Key": API_KEY}


@pytest.fixture
def cors_origin() -> str:
    """The origin the CORS assertions send."""
    return E2E_CORS_ORIGIN


@pytest.fixture(scope="session")
async def api_key_enforced() -> bool:
    """
    Whether the target enforces the API key.

    The demo stack is configured to bypass the key (DEMO_API_KEY_BYPASS), so
    the auth contract cannot be asserted against it - the request is served
    whatever key it carries. The suite asks the target instead of assuming:
    one request without a key, and the answer says whether the key is
    enforced there. The in-process mode always enforces it.
    """
    if not E2E_BASE_URL:
        return True
    async with AsyncClient(base_url=E2E_BASE_URL, timeout=30.0) as client:
        resp = await client.post("/api/v1/search", json={"query": "test"})
    return resp.status_code in (401, 403)


@pytest.fixture
def requires_api_key(api_key_enforced: bool) -> bool:
    """
    The auth assertions only run where the key is enforced.

    Where the target bypasses it, the assertions are skipped with the reason
    - not silently passed, and not turned into their opposite.
    """
    if not api_key_enforced:
        pytest.skip(
            "the target bypasses the API key by design (DEMO_API_KEY_BYPASS) - "
            "the auth contract is asserted where the key is enforced"
        )
    return True
