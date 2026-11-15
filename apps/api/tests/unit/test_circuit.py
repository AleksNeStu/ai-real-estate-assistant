"""Unit tests for utils/circuit.py."""

from datetime import UTC, datetime, timedelta

import pytest

from utils.circuit import (
    AuthenticationError,
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    CircuitBreakerRegistry,
    CircuitState,
    RateLimitError,
    ServerError,
    is_retryable_error,
    with_llm_retry,
)


class TestIsRetryableError:
    def test_rate_limit_429(self):
        assert is_retryable_error(Exception("HTTP 429 Too Many Requests")) is True

    def test_rate_limit_text(self):
        assert is_retryable_error(Exception("Rate limit exceeded")) is True

    def test_server_error_500(self):
        assert is_retryable_error(Exception("HTTP 500 Internal Server Error")) is True

    def test_server_error_502(self):
        assert is_retryable_error(Exception("HTTP 502 Bad Gateway")) is True

    def test_server_error_503(self):
        assert is_retryable_error(Exception("HTTP 503 Service Unavailable")) is True

    def test_server_error_504(self):
        assert is_retryable_error(Exception("HTTP 504 Gateway Timeout")) is True

    def test_connection_error(self):
        assert is_retryable_error(Exception("Connection timeout")) is True

    def test_network_error(self):
        assert is_retryable_error(Exception("Network error")) is True

    def test_dns_error(self):
        assert is_retryable_error(Exception("DNS resolution failed")) is True

    def test_temporary_error(self):
        assert is_retryable_error(Exception("Temporary failure")) is True

    def test_unavailable_error(self):
        assert is_retryable_error(Exception("Service unavailable")) is True

    def test_auth_401_not_retryable(self):
        assert is_retryable_error(Exception("HTTP 401 Unauthorized")) is False

    def test_auth_403_not_retryable(self):
        assert is_retryable_error(Exception("HTTP 403 Forbidden")) is False

    def test_unauthorized_text_not_retryable(self):
        assert is_retryable_error(Exception("Unauthorized access")) is False

    def test_forbidden_text_not_retryable(self):
        assert is_retryable_error(Exception("Forbidden")) is False

    def test_unknown_error_not_retryable(self):
        assert is_retryable_error(Exception("Something went wrong")) is False

    def test_bad_request_not_retryable(self):
        assert is_retryable_error(Exception("HTTP 400 Bad Request")) is False


class TestWithLlmRetry:
    @pytest.mark.asyncio
    async def test_success_no_retry(self):
        call_count = 0

        @with_llm_retry
        async def succeed():
            nonlocal call_count
            call_count += 1
            return "ok"

        result = await succeed()
        assert result == "ok"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_auth_error_no_retry(self):
        call_count = 0

        @with_llm_retry
        async def fail_auth():
            nonlocal call_count
            call_count += 1
            raise Exception("HTTP 401 Unauthorized")

        with pytest.raises(AuthenticationError):
            await fail_auth()
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_rate_limit(self):
        call_count = 0

        @with_llm_retry
        async def rate_limit_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("HTTP 429 Rate limit")
            return "recovered"

        # with_llm_retry uses max_attempts from the decorator call, not the function call
        wrapped = with_llm_retry(rate_limit_then_succeed, max_attempts=3)
        result = await wrapped()
        assert result == "recovered"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retries_on_server_error(self):
        call_count = 0

        async def server_error_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("HTTP 500 Internal Server Error")
            return "recovered"

        wrapped = with_llm_retry(server_error_then_succeed, max_attempts=3)
        result = await wrapped()
        assert result == "recovered"

    @pytest.mark.asyncio
    async def test_raises_after_max_retries(self):
        async def always_fail():
            raise Exception("HTTP 500 Internal Server Error")

        wrapped = with_llm_retry(always_fail, max_attempts=2)
        with pytest.raises(ServerError):
            await wrapped()

    @pytest.mark.asyncio
    async def test_raises_rate_limit_after_max_retries(self):
        async def always_rate_limited():
            raise Exception("HTTP 429 Too Many Requests")

        wrapped = with_llm_retry(always_rate_limited, max_attempts=2)
        with pytest.raises(RateLimitError):
            await wrapped()

    @pytest.mark.asyncio
    async def test_non_retryable_raises_immediately(self):
        call_count = 0

        @with_llm_retry
        async def fail_unknown():
            nonlocal call_count
            call_count += 1
            raise ValueError("Invalid input")

        with pytest.raises(ValueError):
            await fail_unknown()
        assert call_count == 1


class TestCircuitBreakerConfig:
    def test_defaults(self):
        config = CircuitBreakerConfig()
        assert config.failure_threshold == 5
        assert config.success_threshold == 2
        assert config.timeout_seconds == 60.0
        assert config.half_open_max_calls == 1

    def test_custom_config(self):
        config = CircuitBreakerConfig(failure_threshold=3, timeout_seconds=30.0)
        assert config.failure_threshold == 3
        assert config.timeout_seconds == 30.0


class TestCircuitBreaker:
    @pytest.mark.asyncio
    async def test_starts_closed(self):
        cb = CircuitBreaker("test")
        assert cb.stats.current_state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_successful_call(self):
        cb = CircuitBreaker("test")

        async def succeed():
            return "success"

        result = await cb.call(succeed)
        assert result == "success"
        assert cb.stats.successful_calls == 1
        assert cb.stats.failed_calls == 0

    @pytest.mark.asyncio
    async def test_failed_call(self):
        cb = CircuitBreaker("test")

        async def fail():
            raise ValueError("test error")

        with pytest.raises(ValueError):
            await cb.call(fail)
        assert cb.stats.failed_calls == 1

    @pytest.mark.asyncio
    async def test_opens_after_threshold(self):
        config = CircuitBreakerConfig(failure_threshold=3)
        cb = CircuitBreaker("test", config)

        async def fail():
            raise ValueError("error")

        for _ in range(3):
            with pytest.raises(ValueError):
                await cb.call(fail)

        assert cb.stats.current_state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_rejects_when_open(self):
        config = CircuitBreakerConfig(failure_threshold=1)
        cb = CircuitBreaker("test", config)

        async def fail():
            raise ValueError("error")

        with pytest.raises(ValueError):
            await cb.call(fail)

        async def succeed():
            return "should not run"

        with pytest.raises(CircuitBreakerOpenError):
            await cb.call(succeed)

    @pytest.mark.asyncio
    async def test_half_open_after_timeout(self):
        config = CircuitBreakerConfig(failure_threshold=1, timeout_seconds=0.01)
        cb = CircuitBreaker("test", config)

        async def fail():
            raise ValueError("error")

        with pytest.raises(ValueError):
            await cb.call(fail)

        assert cb.stats.current_state == CircuitState.OPEN

        # The cooldown is measured against the WALL clock (datetime.now),
        # whose resolution on Windows is 15.625 ms - coarser than the 10 ms
        # cooldown this test configures. Sleeping for 20 ms therefore does
        # NOT guarantee that the sampled delta reaches the timeout: under a
        # loaded machine the wall clock can advance by less than that across
        # the sleep, the breaker stays OPEN, and the call is rejected. The
        # test failed that way under the parallel unit suite.
        #
        # The state under test is "the cooldown has passed", so the failure
        # timestamp is moved back instead of waiting for it. Same pattern as
        # tests/integration/test_multi_provider_fallback.py.
        cb.stats.last_failure_time = datetime.now(tz=UTC) - timedelta(seconds=1)

        # Next call should go through (half-open -> success -> closed)
        async def recover():
            return "recovered"

        result = await cb.call(recover)
        assert result == "recovered"

    @pytest.mark.asyncio
    async def test_failure_rate_calculation(self):
        cb = CircuitBreaker("test")
        assert cb.stats.failure_rate() == 0.0

        cb.stats.successful_calls = 7
        cb.stats.failed_calls = 3
        assert cb.stats.failure_rate() == pytest.approx(0.3)

    @pytest.mark.asyncio
    async def test_reset(self):
        cb = CircuitBreaker("test")
        cb.stats.failed_calls = 5
        cb.stats.current_state = CircuitState.OPEN
        cb.reset()
        assert cb.stats.current_state == CircuitState.CLOSED
        assert cb.stats.failed_calls == 0


class TestCircuitBreakerRegistry:
    @pytest.mark.asyncio
    async def test_get_breaker(self):
        registry = CircuitBreakerRegistry()
        cb1 = await registry.get_breaker("openai")
        cb2 = await registry.get_breaker("openai")
        assert cb1 is cb2

    @pytest.mark.asyncio
    async def test_different_providers(self):
        registry = CircuitBreakerRegistry()
        cb1 = await registry.get_breaker("openai")
        cb2 = await registry.get_breaker("anthropic")
        assert cb1 is not cb2

    def test_get_all_stats(self):
        registry = CircuitBreakerRegistry()
        registry._breakers["openai"] = CircuitBreaker("openai")
        registry._breakers["anthropic"] = CircuitBreaker("anthropic")
        stats = registry.get_all_stats()
        assert "openai" in stats
        assert "anthropic" in stats

    @pytest.mark.asyncio
    async def test_reset_all(self):
        registry = CircuitBreakerRegistry()
        cb = await registry.get_breaker("openai")
        cb.stats.failed_calls = 5
        await registry.reset_all()
        assert cb.stats.failed_calls == 0

    def test_set_config(self):
        registry = CircuitBreakerRegistry()
        config = CircuitBreakerConfig(failure_threshold=10)
        registry.set_config(config)
        assert registry._config == config
