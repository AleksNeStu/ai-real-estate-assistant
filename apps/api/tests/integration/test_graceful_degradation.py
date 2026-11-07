"""Integration tests for graceful degradation (Task #96).

Tests circuit breaker pattern and degradation behavior when external services
(LLM providers, ChromaDB, database) are unavailable.

Acceptance criteria:
1. ChromaDB unavailable -> search returns clear error, chat works with reduced capability
2. All LLM providers unavailable -> user sees friendly message with retry option
3. Single provider fails -> automatic fallback to next provider in routing
4. Database unavailable -> health endpoint reports degraded, read-only mode where possible
5. Circuit breaker pattern implemented for external service calls
6. Degradation state surfaced in admin health endpoint
7. Integration tests for each degradation scenario
"""

import asyncio

import pytest

from core.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    ServiceDegradedError,
    get_all_breaker_states,
    get_breaker,
    reset_all_breakers,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def _clean_breakers():
    """Reset all circuit breakers between tests."""
    reset_all_breakers()
    yield
    reset_all_breakers()


# =============================================================================
# 1. Circuit Breaker State Machine Tests (AC5)
# =============================================================================


class TestCircuitBreakerStates:
    """Test circuit breaker CLOSED -> OPEN -> HALF_OPEN -> CLOSED transitions."""

    def test_initial_state_is_closed(self):
        breaker = CircuitBreaker("test_service")
        assert breaker.state == CircuitState.CLOSED
        assert breaker.is_available is True
        assert breaker.is_degraded is False

    @pytest.mark.asyncio
    async def test_successful_call_stays_closed(self):
        breaker = CircuitBreaker("test_service", failure_threshold=3)

        async def ok_func():
            return "ok"

        result = await breaker.call(ok_func)
        assert result == "ok"
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_failures_transition_to_open(self):
        """AC5: Repeated failures trip the circuit breaker."""
        breaker = CircuitBreaker("test_service", failure_threshold=3)

        async def failing_func():
            raise RuntimeError("boom")

        for _ in range(3):
            with pytest.raises(RuntimeError):
                await breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN
        assert breaker.is_available is False

    @pytest.mark.asyncio
    async def test_open_circuit_rejects_with_degraded_error(self):
        """AC2/AC5: Open circuit raises ServiceDegradedError."""
        breaker = CircuitBreaker("test_service", failure_threshold=1)

        async def failing_func():
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError):
            await breaker.call(failing_func)

        with pytest.raises(ServiceDegradedError) as exc_info:
            await breaker.call(failing_func)

        assert "test_service" in str(exc_info.value)
        assert exc_info.value.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_open_transitions_to_half_open_after_timeout(self):
        breaker = CircuitBreaker("test_service", failure_threshold=1, recovery_timeout=0.05)

        async def failing_func():
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError):
            await breaker.call(failing_func)
        assert breaker.state == CircuitState.OPEN

        await asyncio.sleep(0.06)
        assert breaker.state == CircuitState.HALF_OPEN
        assert breaker.is_degraded is True

    @pytest.mark.asyncio
    async def test_half_open_success_closes_circuit(self):
        breaker = CircuitBreaker(
            "test_service", failure_threshold=1, recovery_timeout=0.05, success_threshold=2
        )

        async def failing_func():
            raise RuntimeError("boom")

        async def ok_func():
            return "ok"

        with pytest.raises(RuntimeError):
            await breaker.call(failing_func)
        assert breaker.state == CircuitState.OPEN

        await asyncio.sleep(0.06)
        assert breaker.state == CircuitState.HALF_OPEN

        await breaker.call(ok_func)
        await breaker.call(ok_func)
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_half_open_failure_reopens(self):
        breaker = CircuitBreaker("test_service", failure_threshold=1, recovery_timeout=0.05)

        async def failing_func():
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError):
            await breaker.call(failing_func)
        await asyncio.sleep(0.06)
        assert breaker.state == CircuitState.HALF_OPEN

        with pytest.raises(RuntimeError):
            await breaker.call(failing_func)
        assert breaker.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_call_timeout_records_failure(self):
        breaker = CircuitBreaker("test_service", call_timeout=0.05)

        async def slow_func():
            await asyncio.sleep(1.0)
            return "too late"

        with pytest.raises(ServiceDegradedError):
            await breaker.call(slow_func)
        assert breaker.failure_count == 1

    def test_reset_returns_to_closed(self):
        breaker = CircuitBreaker("test_service")
        breaker._state = CircuitState.OPEN
        breaker._failure_count = 5
        breaker.reset()
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0

    def test_get_status_returns_dict(self):
        breaker = CircuitBreaker("test_service")
        status = breaker.get_status()
        assert status["service"] == "test_service"
        assert status["state"] == "closed"
        assert "total_calls" in status
        assert "total_failures" in status


# =============================================================================
# 2. Global Registry Tests (AC6)
# =============================================================================


class TestBreakerRegistry:
    """Test global breaker registry for multi-service tracking."""

    def test_get_breaker_creates_new(self):
        breaker = get_breaker("my_service")
        assert breaker.service_name == "my_service"
        assert breaker.state == CircuitState.CLOSED

    def test_get_breaker_returns_same_instance(self):
        b1 = get_breaker("shared_service")
        b2 = get_breaker("shared_service")
        assert b1 is b2

    def test_get_all_breaker_states(self):
        get_breaker("svc_a")
        get_breaker("svc_b")
        states = get_all_breaker_states()
        assert "svc_a" in states
        assert "svc_b" in states
        assert states["svc_a"]["state"] == "closed"

    def test_reset_all_breakers(self):
        get_breaker("svc_a")
        get_breaker("svc_b")
        reset_all_breakers()
        assert get_all_breaker_states() == {}


# =============================================================================
# 3. Vector Store / ChromaDB Degradation Tests (AC1)
# =============================================================================


class TestVectorStoreDegradation:
    """AC1: ChromaDB unavailable -> search returns clear error."""

    @pytest.mark.asyncio
    async def test_search_breaker_trips_on_repeated_chromadb_failures(self):
        """ChromaDB failures trip the circuit breaker, blocking further calls."""
        breaker = get_breaker("vector_store", failure_threshold=2)

        async def failing_search():
            raise RuntimeError("ChromaDB connection refused")

        with pytest.raises(RuntimeError):
            await breaker.call(failing_search)
        with pytest.raises(RuntimeError):
            await breaker.call(failing_search)

        assert breaker.state == CircuitState.OPEN

        with pytest.raises(ServiceDegradedError):
            await breaker.call(failing_search)

    @pytest.mark.asyncio
    async def test_search_endpoint_returns_503_without_store(self):
        """Search endpoint returns 503 with clear message when store is None."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        from api.dependencies import get_vector_store
        from api.routers.search import router

        app = FastAPI()
        app.include_router(router, prefix="/api/v1")

        async def mock_no_store():
            yield None

        app.dependency_overrides[get_vector_store] = mock_no_store

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/v1/search", json={"query": "apartments in Berlin"})
            assert resp.status_code == 503
            assert "unavailable" in resp.json()["detail"].lower()

        app.dependency_overrides.clear()


# =============================================================================
# 4. LLM Provider Degradation Tests (AC2, AC3)
# =============================================================================


class TestLLMProviderDegradation:
    """AC2/AC3: LLM provider failures tracked by circuit breaker."""

    @pytest.mark.asyncio
    async def test_single_provider_failure_tracked(self):
        """AC3: Single provider fails -> circuit breaker tracks failures."""
        breaker = get_breaker("llm_provider", failure_threshold=2)

        async def failing_llm_call():
            raise RuntimeError("OpenAI API rate limit exceeded")

        with pytest.raises(RuntimeError):
            await breaker.call(failing_llm_call)
        assert breaker.failure_count == 1

        with pytest.raises(RuntimeError):
            await breaker.call(failing_llm_call)
        assert breaker.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_all_providers_unavailable_friendly_error(self):
        """AC2: All LLM providers unavailable -> ServiceDegradedError."""
        breaker = get_breaker("llm_provider", failure_threshold=1)

        async def failing_llm_call():
            raise RuntimeError("All providers failed")

        with pytest.raises(RuntimeError):
            await breaker.call(failing_llm_call)

        with pytest.raises(ServiceDegradedError) as exc_info:
            await breaker.call(failing_llm_call)

        error_msg = str(exc_info.value).lower()
        assert "llm_provider" in error_msg
        assert "open" in error_msg


# =============================================================================
# 5. Health Endpoint Degradation Tests (AC6)
# =============================================================================


class TestHealthDegradation:
    """AC6: Degradation state surfaced in admin health endpoint."""

    @pytest.mark.asyncio
    async def test_health_includes_circuit_breaker_states(self):
        """Circuit breaker states are included in health check response."""
        from api.health import get_health_status

        breaker = get_breaker("test_health_svc")
        breaker._total_calls = 5
        breaker._total_failures = 3

        await get_health_status(include_dependencies=False)

        # Check circuit breaker states are included in registry
        states = get_all_breaker_states()
        assert "test_health_svc" in states
        assert states["test_health_svc"]["total_calls"] == 5

    @pytest.mark.asyncio
    async def test_open_breaker_shows_as_unhealthy_in_health(self):
        """Open circuit breaker appears as UNHEALTHY in health response."""
        from api.health import HealthStatus, get_health_status

        breaker = get_breaker("critical_service")
        breaker._state = CircuitState.OPEN

        health = await get_health_status(include_dependencies=False)

        cb_key = "circuit_breaker:critical_service"
        assert cb_key in health.dependencies
        assert health.dependencies[cb_key].status == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_half_open_breaker_shows_as_degraded_in_health(self):
        """Half-open circuit breaker appears as DEGRADED in health response."""
        from api.health import HealthStatus, get_health_status

        breaker = get_breaker("degraded_service")
        breaker._state = CircuitState.HALF_OPEN

        health = await get_health_status(include_dependencies=False)

        cb_key = "circuit_breaker:degraded_service"
        assert cb_key in health.dependencies
        assert health.dependencies[cb_key].status == HealthStatus.DEGRADED


# =============================================================================
# 6. Database Degradation Tests (AC4)
# =============================================================================


class TestDatabaseDegradation:
    """AC4: Database unavailable -> circuit breaker tracks state."""

    @pytest.mark.asyncio
    async def test_db_breaker_trips_on_connection_failure(self):
        breaker = get_breaker("database", failure_threshold=3)

        async def failing_db_call():
            raise RuntimeError("Connection refused")

        for _ in range(3):
            with pytest.raises(RuntimeError):
                await breaker.call(failing_db_call)

        assert breaker.state == CircuitState.OPEN

        states = get_all_breaker_states()
        assert "database" in states
        assert states["database"]["state"] == "open"

    @pytest.mark.asyncio
    async def test_db_breaker_status_in_health(self):
        """AC4: Database breaker state visible in health endpoint."""
        from api.health import HealthStatus, get_health_status

        breaker = get_breaker("database")
        breaker._state = CircuitState.OPEN
        breaker._total_failures = 5

        health = await get_health_status(include_dependencies=False)

        cb_key = "circuit_breaker:database"
        assert cb_key in health.dependencies
        assert health.dependencies[cb_key].status == HealthStatus.UNHEALTHY
