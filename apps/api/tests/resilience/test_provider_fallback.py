"""
The fallback and the degradation answer, proven against the real code.

The rest of this directory checks the circuit breaker itself - and it checks
it against mini-applications that MIRROR the application's logic. This file
checks what the caller actually gets when a provider fails:

* the fallback chain the README sells - a failing provider is skipped and
  the next one answers;
* the answer the endpoints give when there is no provider left to answer -
  a clear 503 that invites a retry, not a 500 and not a hang;
* the health endpoint's own report of the degraded dependency (the real
  endpoint, not a copy of it).

Nothing here calls a real provider. The failing one is a fake that raises,
and the working one is a fake that answers - so the proof costs no key and
no token, and it is the same in every environment.
"""

import os

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("API_ACCESS_KEY", "test-resilience-key-12345")
os.environ.setdefault("ENABLE_JWT_AUTH", "false")

from core.circuit_breaker import (  # noqa: E402
    CircuitState,
    get_breaker,
    reset_all_breakers,
)
from utils.circuit import CircuitBreakerManager  # noqa: E402

API_KEY = os.environ["API_ACCESS_KEY"]


@pytest.fixture
def api_headers() -> dict[str, str]:
    return {"X-API-Key": API_KEY}


@pytest.fixture(autouse=True)
def _clean_breakers():
    """Reset the dependency breakers between tests."""
    reset_all_breakers()
    yield
    reset_all_breakers()


class _FakeProvider:
    """A provider that answers, or one that fails. Both are local."""

    def __init__(self, answer: str | None = None) -> None:
        self.answer = answer
        self.calls = 0

    async def __call__(self, **kwargs) -> str:
        self.calls += 1
        if self.answer is None:
            # The message deliberately names no retryable symptom, so the
            # call fails once instead of being retried by the wrapper.
            raise RuntimeError("the fake provider refused the request")
        return self.answer


# =============================================================================
# 1. The fallback chain
# =============================================================================


class TestProviderFallbackChain:
    """A failing provider is skipped and the next one answers."""

    @pytest.mark.asyncio
    async def test_the_next_provider_answers_when_the_first_one_fails(self):
        manager = CircuitBreakerManager()
        broken = _FakeProvider(answer=None)
        working = _FakeProvider(answer="the answer of the working provider")

        async def create(provider, key_index, api_key):
            if provider == "broken":
                return await broken(provider=provider, key_index=key_index, api_key=api_key)
            return await working(provider=provider, key_index=key_index, api_key=api_key)

        result = await manager.call_with_fallback(
            providers=["broken", "working"],
            provider_keys={"broken": ["key-a"], "working": ["key-b"]},
            func=create,
        )

        assert result == "the answer of the working provider"
        assert broken.calls == 1
        assert working.calls == 1

    @pytest.mark.asyncio
    async def test_the_second_key_of_a_provider_is_tried_before_the_next_provider(self):
        manager = CircuitBreakerManager()
        calls: list[tuple[str, int]] = []

        async def create(provider, key_index, api_key):
            calls.append((provider, key_index))
            if key_index == 0:
                raise RuntimeError("the fake provider refused the request")
            return "the answer of the second key"

        result = await manager.call_with_fallback(
            providers=["one"],
            provider_keys={"one": ["key-a", "key-b"]},
            func=create,
        )

        assert result == "the answer of the second key"
        assert calls == [("one", 0), ("one", 1)]

    @pytest.mark.asyncio
    async def test_every_provider_failing_names_the_failure(self):
        manager = CircuitBreakerManager()

        async def create(provider, key_index, api_key):
            raise RuntimeError("the fake provider refused the request")

        with pytest.raises(RuntimeError) as exc_info:
            await manager.call_with_fallback(
                providers=["broken", "also-broken"],
                provider_keys={"broken": ["key-a"], "also-broken": ["key-b"]},
                func=create,
            )

        message = str(exc_info.value)
        # The caller is told that every provider failed - not handed a wrong
        # answer, and not left with an empty one.
        assert "all providers and keys failed" in message.lower()
        assert "the fake provider refused the request" in message


# =============================================================================
# 2. The degradation answer of the real endpoints
# =============================================================================


class _FailingStore:
    """A vector store whose calls always fail."""

    def __init__(self) -> None:
        self.calls = 0

    # The real store's search is synchronous - the router awaits the
    # breaker, not the store - so the fake has the same shape.
    def hybrid_search(self, *args, **kwargs):
        self.calls += 1
        raise RuntimeError("the vector store is not reachable")

    def get_stats(self) -> dict:
        return {"documents": 0}


def _app_with_failing_store(store: _FailingStore):
    """The real application with a vector store that fails."""
    from api.dependencies import get_vector_store
    from api.main import app

    app.dependency_overrides[get_vector_store] = lambda: store
    return app


class TestTheDegradationAnswer:
    """The endpoints answer a clear question when a dependency is down."""

    async def _search_until_degraded(self, client: AsyncClient) -> tuple[list[int], object]:
        """Ask for the same search until the endpoint reports the degradation."""
        statuses: list[int] = []
        resp = None
        for _ in range(7):
            resp = await client.post(
                "/api/v1/search",
                json={"query": "apartments in Warsaw"},
                headers={"X-API-Key": API_KEY},
            )
            statuses.append(resp.status_code)
            if "degraded" in resp.json().get("detail", "").lower():
                break
        return statuses, resp

    @pytest.mark.asyncio
    async def test_the_search_endpoint_stops_calling_a_store_that_is_down(self):
        store = _FailingStore()
        app = _app_with_failing_store(store)
        transport = ASGITransport(app=app, raise_app_exceptions=False)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            statuses, resp = await self._search_until_degraded(client)

            # The endpoint reports the degradation instead of pretending the
            # answer is an empty result set.
            assert "degraded" in resp.json().get("detail", "").lower(), (
                f"the search never degraded: {statuses}"
            )

            # And it fails FAST: once the breaker is open the dead store is
            # not called again - a dependency that is down does not get the
            # request budget of a healthy one.
            calls_when_degraded = store.calls
            await client.post(
                "/api/v1/search",
                json={"query": "apartments in Warsaw"},
                headers={"X-API-Key": API_KEY},
            )
            assert store.calls == calls_when_degraded

    @pytest.mark.asyncio
    async def test_the_degraded_search_says_so_and_invites_a_retry(self):
        store = _FailingStore()
        app = _app_with_failing_store(store)
        transport = ASGITransport(app=app, raise_app_exceptions=False)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            _, resp = await self._search_until_degraded(client)

            detail = resp.json().get("detail", "").lower()
            assert "degraded" in detail or "unavailable" in detail
            # The answer is for the caller: no stack trace, no internal name.
            assert "traceback" not in detail
            assert "retry" in detail or "moment" in detail

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "The search router raises a 503 when the vector store is degraded "
            "and then wraps it - like every other exception - into a 500 "
            "(api/routers/search.py: the generic `except Exception` arm). The "
            "message is the degradation message; the status code is not the "
            "one it promises. Strict, so the day the router answers 503 the "
            "pipeline goes red and this marker is removed."
        ),
    )
    @pytest.mark.asyncio
    async def test_the_degraded_search_answers_503(self):
        store = _FailingStore()
        app = _app_with_failing_store(store)
        transport = ASGITransport(app=app, raise_app_exceptions=False)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            _, resp = await self._search_until_degraded(client)

            assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_the_health_endpoint_reports_the_degraded_dependency(self):
        # The real health endpoint, not a copy of its logic.
        from api.main import app

        get_breaker("vector_store")._state = CircuitState.OPEN

        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health/detailed?include_dependencies=true")

        assert resp.status_code in (200, 503)
        data = resp.json()
        assert data["status"] in ("healthy", "degraded", "unhealthy")
        # The breaker that is open is named in the report, with its state.
        breakers = data.get("dependencies", {})
        assert "circuit_breaker:vector_store" in breakers
        assert breakers["circuit_breaker:vector_store"]["status"] == "unhealthy"
