import asyncio
import sys
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import api.dependencies as api_dependencies
import api.health as health_module
from api.health import (
    DependencyHealth,
    HealthCheckResponse,
    HealthStatus,
    check_database,
    check_llm_provider,
    check_redis,
    check_vector_store,
    get_health_status,
    require_healthy,
)

# The two health tests below were marked `xfail(strict=False)` for years
# (F-20260903-01 / F-20260903-02), which meant they could never fail the
# build — and therefore documented nothing. They are now ordinary, enforcing
# tests on every platform: the dependency checks are patched on the module
# object, and the slow check's sleep outlasts both timers, so the outcome
# cannot depend on what happens to be installed on the machine or on which
# timer a loaded event loop processes first.
#
# `test_the_patch_seam_holds` pins the property that makes them deterministic:
# the module the test patches must be the module the function under test reads
# its globals from.


class FakeResponse:
    def __init__(self, status_code: int):
        self.status_code = status_code


class FakeAsyncClient:
    def __init__(self, status_code: int):
        self._status_code = status_code

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def get(self, url):
        return FakeResponse(self._status_code)


class FakeRedisClient:
    def __init__(self, should_fail: bool):
        self._should_fail = should_fail

    def ping(self):
        if self._should_fail:
            raise RuntimeError("redis down")
        return "PONG"

    def close(self):
        return None


@pytest.mark.asyncio
async def test_check_redis_returns_none_when_not_configured(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    result = await check_redis()
    assert result is None


@pytest.mark.asyncio
async def test_check_redis_reports_healthy_when_ping_succeeds(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    fake_module = SimpleNamespace(from_url=lambda *_args, **_kwargs: FakeRedisClient(False))
    monkeypatch.setitem(sys.modules, "redis", fake_module)
    result = await check_redis()
    assert result is not None
    assert result.status == HealthStatus.HEALTHY
    assert result.message == "OK"


@pytest.mark.asyncio
async def test_check_redis_reports_unhealthy_on_error(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    fake_module = SimpleNamespace(from_url=lambda *_args, **_kwargs: FakeRedisClient(True))
    monkeypatch.setitem(sys.modules, "redis", fake_module)
    result = await check_redis()
    assert result is not None
    assert result.status == HealthStatus.UNHEALTHY
    assert result.message.startswith("Error:")


@pytest.mark.asyncio
async def test_check_llm_provider_degraded_without_providers(monkeypatch):
    settings = SimpleNamespace(
        openai_api_key=None,
        anthropic_api_key=None,
        google_api_key=None,
        grok_api_key=None,
        deepseek_api_key=None,
        default_provider="openai",
    )
    fake_httpx = SimpleNamespace(AsyncClient=lambda timeout=2.0: FakeAsyncClient(404))
    monkeypatch.setitem(sys.modules, "httpx", fake_httpx)
    monkeypatch.setattr(health_module, "get_settings", lambda: settings)
    result = await check_llm_provider()
    assert result.status == HealthStatus.DEGRADED
    assert result.details == {"configured_providers": []}


@pytest.mark.asyncio
async def test_check_llm_provider_includes_ollama_when_available(monkeypatch):
    settings = SimpleNamespace(
        openai_api_key=None,
        anthropic_api_key=None,
        google_api_key=None,
        grok_api_key=None,
        deepseek_api_key=None,
        default_provider="openai",
    )
    fake_httpx = SimpleNamespace(AsyncClient=lambda timeout=2.0: FakeAsyncClient(200))
    monkeypatch.setitem(sys.modules, "httpx", fake_httpx)
    monkeypatch.setattr(health_module, "get_settings", lambda: settings)
    result = await check_llm_provider()
    assert result.status == HealthStatus.HEALTHY
    assert result.details == {"configured_providers": ["ollama"], "default": "openai"}


@pytest.mark.asyncio
async def test_check_llm_provider_healthy_with_configured_key(monkeypatch):
    settings = SimpleNamespace(
        openai_api_key="sk-test",
        anthropic_api_key=None,
        google_api_key=None,
        grok_api_key=None,
        deepseek_api_key=None,
        default_provider="openai",
    )
    fake_httpx = SimpleNamespace(AsyncClient=lambda timeout=2.0: FakeAsyncClient(500))
    monkeypatch.setitem(sys.modules, "httpx", fake_httpx)
    monkeypatch.setattr(health_module, "get_settings", lambda: settings)
    result = await check_llm_provider()
    assert result.status == HealthStatus.HEALTHY
    assert result.details == {"configured_providers": ["openai"], "default": "openai"}


def test_the_patch_seam_holds():
    """The module the test patches must be the module the function reads from.

    This is the property the two tests below depend on, and the reason they
    used to be marked `xfail`: a dotted import path ("api.health.X") makes the
    patcher IMPORT the module by name, and that import can resolve to a
    different module object than the one the function under test was imported
    from. The patch then lands on a copy, the real check runs, and the test
    fails for a reason that has nothing to do with the code under test.

    On the CI image the symptom was "the vector store was healthy"; on a
    machine without chromadb the same test passed for the wrong reason. The
    seam check turns that class of mystery into one precise assertion, on
    every platform.
    """
    assert get_health_status.__globals__ is health_module.__dict__
    assert health_module is sys.modules["api.health"]


@pytest.mark.asyncio
async def test_get_health_status_unhealthy_when_vector_store_unhealthy(monkeypatch):
    """Test that health status is UNHEALTHY when the vector store dependency
    check reports UNHEALTHY.

    The dependency checks are patched on the module OBJECT (see the import at
    the top of this file), not through a dotted import path — a dotted path
    makes monkeypatch import the module by name, which can resolve to a
    different module object than the one ``get_health_status`` reads its
    globals from. When that happened the real vector-store check ran, reported
    healthy, and the overall status came back healthy instead of unhealthy.

    On the CI image that failure looked like a chromadb problem, but chromadb
    was only the messenger: the real check succeeded because a live store was
    installed there, while on a machine without it the same test passed for the
    wrong reason (the check reported "not initialized"). Replacing the check
    itself makes the outcome identical on every platform.

    See F-20260903-01 in the findings ledger and TaskMaster #20.
    """
    settings = SimpleNamespace(version="9.9.9", database_url=None)

    async def _vector_unhealthy():
        return DependencyHealth(
            name="vector_store",
            status=HealthStatus.UNHEALTHY,
            message="vector store not initialized",
        )

    async def _redis_healthy():
        return DependencyHealth(
            name="redis",
            status=HealthStatus.HEALTHY,
            message="ok",
        )

    async def _database_none():
        return None

    async def _llm_healthy():
        return DependencyHealth(
            name="llm_providers",
            status=HealthStatus.HEALTHY,
            message="ok",
        )

    # Patch the module OBJECT, not a dotted import path. A dotted path makes
    # monkeypatch import the module by name, which can resolve to a DIFFERENT
    # module object than the one this test file imported at collection time —
    # and then the patch lands on a copy while the function under test keeps
    # using the original globals. That is what made this test fail under a
    # loaded parallel run: the real vector-store check ran, reported healthy,
    # and the overall status came back healthy instead of unhealthy.
    monkeypatch.setattr(health_module, "get_settings", lambda: settings)
    monkeypatch.setattr(health_module, "check_vector_store", _vector_unhealthy)
    monkeypatch.setattr(health_module, "check_redis", _redis_healthy)
    monkeypatch.setattr(health_module, "check_database", _database_none)
    monkeypatch.setattr(health_module, "check_llm_provider", _llm_healthy)

    result = await get_health_status(include_dependencies=True)
    assert result.status == HealthStatus.UNHEALTHY
    assert result.dependencies["vector_store"].status == HealthStatus.UNHEALTHY
    assert result.version == "9.9.9"


@pytest.mark.asyncio
async def test_a_circuit_breaker_does_not_shadow_the_vector_store_dependency(monkeypatch):
    """A breaker named "vector_store" must not overwrite the real dependency.

    The search path registers a circuit breaker named "vector_store". The health
    payload used to key the breaker entries by the RAW breaker name, so that
    breaker overwrote the vector-store dependency check in the same dictionary.

    Two things broke because of it: the health report showed the breaker's
    state instead of the store's, and `/health/ready` — which reads
    ``dependencies["vector_store"]`` — reported "ready" while the vector store
    was unhealthy. Kubernetes would have kept routing traffic to the pod.
    """
    from core.circuit_breaker import CircuitState, get_breaker, reset_all_breakers

    reset_all_breakers()
    try:
        breaker = get_breaker("vector_store")
        breaker._state = CircuitState.OPEN

        settings = SimpleNamespace(version="1.0.0")

        async def _vector_unhealthy():
            return DependencyHealth(
                name="vector_store",
                status=HealthStatus.UNHEALTHY,
                message="vector store not initialized",
            )

        async def _none():
            return None

        monkeypatch.setattr(health_module, "check_vector_store", _vector_unhealthy)
        monkeypatch.setattr(health_module, "check_redis", _none)
        monkeypatch.setattr(health_module, "check_database", _none)
        monkeypatch.setattr(health_module, "check_llm_provider", _none)
        monkeypatch.setattr(health_module, "get_settings", lambda: settings)

        result = await get_health_status(include_dependencies=True)

        # The dependency check keeps the key it owns...
        assert result.dependencies["vector_store"].status == HealthStatus.UNHEALTHY
        # ...and the breaker is reported under its own prefixed key.
        assert "circuit_breaker:vector_store" in result.dependencies
        assert result.dependencies["circuit_breaker:vector_store"].status == HealthStatus.UNHEALTHY
        # An unhealthy vector store makes the whole endpoint unhealthy.
        assert result.status == HealthStatus.UNHEALTHY
    finally:
        reset_all_breakers()


@pytest.mark.asyncio
async def test_check_vector_store_uses_thread_for_blocking_count(monkeypatch):
    """The blocking ChromaDB count must be off the event loop."""

    import threading

    class _CountProbe:
        def __init__(self):
            self.invoked_on = None
            self.call_count = 0

        def count(self):
            self.call_count += 1
            self.invoked_on = threading.get_ident()
            return 42

    probe = _CountProbe()
    fake_store = SimpleNamespace(_collection=probe)

    # Drop any cached result so the patched callable is exercised.
    api_dependencies.get_vector_store.cache_clear()

    def _fake_get_vector_store():
        return fake_store

    # Patch the symbol bound into the api.health module so the new
    # asyncio.to_thread wrapping is exercised end-to-end.
    monkeypatch.setattr(health_module, "get_vector_store", _fake_get_vector_store)

    loop_thread = threading.get_ident()
    result = await check_vector_store()

    assert result.status == HealthStatus.HEALTHY
    assert probe.call_count == 1
    assert result.details == {"item_count": 42}
    assert probe.invoked_on is not None
    assert probe.invoked_on != loop_thread


@pytest.mark.asyncio
async def test_get_health_status_marks_slow_dependency_degraded(monkeypatch):
    """A slow dependency check must not block the response and must be DEGRADED.

    The dependency checks are patched on the module OBJECT, not through a dotted
    import path — see the note on the test above. See F-20260903-02 in the
    findings ledger and TaskMaster #20.
    """
    settings = SimpleNamespace(version="1.0.0")

    async def _slow_vector():
        # The sleep is deliberately far longer than both the handler's internal
        # budget (4s) and the outer wait_for below (30s). With a shorter sleep
        # the outcome depended on which of the two timers the event loop
        # happened to process first on a loaded runner: when the loop was
        # blocked long enough for the sleep to finish, the check returned
        # HEALTHY and the test failed for no reason. Now the sleep cannot
        # possibly win, so the only reachable outcome is DEGRADED — or a loud
        # TimeoutError from the outer wait_for if the runner stalls outright.
        await asyncio.sleep(60)
        return DependencyHealth(
            name="vector_store",
            status=HealthStatus.HEALTHY,
            message="should not be reached",
        )

    async def _ok_redis():
        return None

    async def _ok_database():
        return None

    async def _ok_llm():
        return DependencyHealth(
            name="llm_providers",
            status=HealthStatus.HEALTHY,
            message="ok",
        )

    monkeypatch.setattr(health_module, "check_vector_store", _slow_vector)
    monkeypatch.setattr(health_module, "check_redis", _ok_redis)
    monkeypatch.setattr(health_module, "check_database", _ok_database)
    monkeypatch.setattr(health_module, "check_llm_provider", _ok_llm)
    monkeypatch.setattr(health_module, "get_settings", lambda: settings)

    started = asyncio.get_event_loop().time()
    status_task = asyncio.create_task(get_health_status(include_dependencies=True))
    # The health handler bounds each dependency check at 4s internally. The outer
    # wait_for is a safety net, not the assertion - it is deliberately generous,
    # because a saturated CI runner can delay the event loop's timers by several
    # seconds and a tight outer bound turned this test into a load-sensitive
    # flake (it failed on a busy runner and passed on an idle one).
    result = await asyncio.wait_for(status_task, timeout=30.0)
    elapsed = asyncio.get_event_loop().time() - started

    assert elapsed < 25.0, f"the health response waited {elapsed:.1f}s for a bounded check"
    assert result.dependencies["vector_store"].status == HealthStatus.DEGRADED
    assert "Timed out" in result.dependencies["vector_store"].message


@pytest.mark.asyncio
async def test_require_healthy_raises_on_unhealthy_dependencies(monkeypatch):
    response = HealthCheckResponse(
        status=HealthStatus.UNHEALTHY,
        version="1.0.0",
        timestamp="2026-01-01T00:00:00Z",
        dependencies={
            "vector_store": DependencyHealth(
                name="vector_store",
                status=HealthStatus.UNHEALTHY,
                message="down",
            ),
            "redis": DependencyHealth(
                name="redis",
                status=HealthStatus.HEALTHY,
                message="ok",
            ),
        },
        uptime_seconds=1.0,
    )

    async def _fake_get_health_status(*_args, **_kwargs):
        return response

    monkeypatch.setattr(health_module, "get_health_status", _fake_get_health_status)
    with pytest.raises(HTTPException) as exc_info:
        await require_healthy()
    assert "vector_store" in str(exc_info.value.detail)


# Tests for check_database
@pytest.mark.asyncio
async def test_check_database_returns_none_when_not_configured(monkeypatch):
    """Database check returns None when DATABASE_URL is not set."""
    settings = SimpleNamespace(database_url=None)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(health_module, "get_settings", lambda: settings)
    result = await check_database()
    assert result is None


@pytest.mark.asyncio
async def test_check_database_healthy_when_connection_succeeds(monkeypatch):
    """Database check returns healthy when connection succeeds."""
    settings = SimpleNamespace(database_url="sqlite+aiosqlite:///test.db")

    # Create fake engine and connection
    class FakeConnection:
        async def execute(self, text):
            return None

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

    class FakeEngine:
        def connect(self):
            return FakeConnection()

    fake_sqlalchemy = SimpleNamespace(text=lambda s: s)
    fake_database = SimpleNamespace(get_engine=lambda: FakeEngine())

    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///test.db")
    monkeypatch.setattr(health_module, "get_settings", lambda: settings)
    monkeypatch.setitem(sys.modules, "sqlalchemy", fake_sqlalchemy)
    monkeypatch.setitem(sys.modules, "db.database", fake_database)

    result = await check_database()
    assert result is not None
    assert result.status == HealthStatus.HEALTHY
    assert result.message == "OK"


@pytest.mark.asyncio
async def test_check_database_unhealthy_on_error(monkeypatch):
    """Database check returns unhealthy when connection fails."""
    settings = SimpleNamespace(database_url="postgresql://invalid:5432/db")

    class FakeEngine:
        def connect(self):
            raise RuntimeError("Connection refused")

    fake_sqlalchemy = SimpleNamespace(text=lambda s: s)
    fake_database = SimpleNamespace(get_engine=lambda: FakeEngine())

    monkeypatch.setenv("DATABASE_URL", "postgresql://invalid:5432/db")
    monkeypatch.setattr(health_module, "get_settings", lambda: settings)
    monkeypatch.setitem(sys.modules, "sqlalchemy", fake_sqlalchemy)
    monkeypatch.setitem(sys.modules, "db.database", fake_database)

    result = await check_database()
    assert result is not None
    assert result.status == HealthStatus.UNHEALTHY
    assert result.message.startswith("Error:")
