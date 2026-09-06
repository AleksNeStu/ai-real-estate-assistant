"""
Comprehensive unit tests for data/adapters/base.py.

Covers:
- with_retry: sync retry decorator with exponential backoff
- with_retry_async: async retry decorator
- PortalFilter: dataclass, to_dict, __str__
- PortalFetchResult: dataclass, to_dataframe, add_error
- ExternalSourceAdapter: abstract base, configuration, status, URL building
- RateLimiter: token bucket algorithm, acquire, reset
"""

import time
from datetime import datetime

import pandas as pd
import pytest

from data.adapters.base import (
    MAX_RETRIES,
    RETRY_MAX_WAIT,
    RETRYABLE_EXCEPTIONS,
    ExternalSourceAdapter,
    PortalFetchResult,
    PortalFilter,
    RateLimiter,
    with_retry,
    with_retry_async,
)

# ---------------------------------------------------------------------------
# with_retry decorator
# ---------------------------------------------------------------------------


class TestWithRetry:
    """Tests for the with_retry sync decorator."""

    def test_successful_call_no_retry(self):
        """Function succeeds on first attempt - no retries."""
        call_count = 0

        @with_retry(max_tries=3)
        def succeed():
            nonlocal call_count
            call_count += 1
            return "ok"

        result = succeed()
        assert result == "ok"
        assert call_count == 1

    def test_retries_on_connection_error(self):
        """Retries on ConnectionError, eventually succeeds."""
        call_count = 0

        @with_retry(max_tries=3)
        def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("network down")
            return "recovered"

        result = flaky()
        assert result == "recovered"
        assert call_count == 3

    def test_retries_on_timeout_error(self):
        call_count = 0

        @with_retry(max_tries=3)
        def timeout_fn():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise TimeoutError("timed out")
            return "ok"

        result = timeout_fn()
        assert result == "ok"
        assert call_count == 2

    def test_retries_on_os_error(self):
        call_count = 0

        @with_retry(max_tries=3)
        def os_fail():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise OSError("socket error")
            return "ok"

        result = os_fail()
        assert result == "ok"

    def test_raises_after_max_retries(self):
        """Exhausts all retries and raises the exception."""
        call_count = 0

        @with_retry(max_tries=3)
        def always_fail():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("persistent failure")

        with pytest.raises(ConnectionError, match="persistent failure"):
            always_fail()
        assert call_count == 3

    def test_non_retryable_exception_not_retried(self):
        """ValueError is not in RETRYABLE_EXCEPTIONS, so it's not retried."""
        call_count = 0

        @with_retry(max_tries=3)
        def value_err():
            nonlocal call_count
            call_count += 1
            raise ValueError("bad value")

        with pytest.raises(ValueError):
            value_err()
        assert call_count == 1

    def test_on_retry_callback_called(self):
        """on_retry callback receives attempt, wait_time, exception."""
        retry_events = []

        def on_retry(attempt, wait_time, exception):
            retry_events.append((attempt, wait_time, type(exception).__name__))

        @with_retry(max_tries=3, on_retry=on_retry)
        def fail_once():
            if fail_once.call_count == 0:
                fail_once.call_count += 1
                raise ConnectionError("temporary")
            return "ok"

        fail_once.call_count = 0
        result = fail_once()
        assert result == "ok"
        assert len(retry_events) == 1
        assert retry_events[0][2] == "ConnectionError"

    def test_preserves_function_name(self):
        @with_retry(max_tries=3)
        def my_function():
            pass

        assert my_function.__name__ == "my_function"

    def test_default_max_retries(self):
        """Uses MAX_RETRIES default when not overridden."""
        assert MAX_RETRIES == 3

    def test_default_max_wait(self):
        assert RETRY_MAX_WAIT == 30


# ---------------------------------------------------------------------------
# with_retry_async decorator
# ---------------------------------------------------------------------------


class TestWithRetryAsync:
    """Tests for the with_retry_async decorator."""

    @pytest.mark.asyncio
    async def test_successful_async_call(self):
        call_count = 0

        @with_retry_async(max_tries=3)
        async def succeed():
            nonlocal call_count
            call_count += 1
            return "ok"

        result = await succeed()
        assert result == "ok"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_connection_error(self):
        call_count = 0

        @with_retry_async(max_tries=3)
        async def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("async network down")
            return "recovered"

        result = await flaky()
        assert result == "recovered"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_raises_after_max_retries(self):
        call_count = 0

        @with_retry_async(max_tries=2)
        async def always_fail():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("always")

        with pytest.raises(ConnectionError):
            await always_fail()
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_non_retryable_not_retried(self):
        call_count = 0

        @with_retry_async(max_tries=3)
        async def value_err():
            nonlocal call_count
            call_count += 1
            raise ValueError("async bad value")

        with pytest.raises(ValueError):
            await value_err()
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_preserves_function_name(self):
        @with_retry_async(max_tries=3)
        async def my_async_fn():
            pass

        assert my_async_fn.__name__ == "my_async_fn"


# ---------------------------------------------------------------------------
# RETRYABLE_EXCEPTIONS
# ---------------------------------------------------------------------------


class TestRetryableExceptions:
    """Tests for the RETRYABLE_EXCEPTIONS tuple."""

    def test_includes_connection_error(self):
        assert ConnectionError in RETRYABLE_EXCEPTIONS

    def test_includes_timeout_error(self):
        assert TimeoutError in RETRYABLE_EXCEPTIONS

    def test_includes_os_error(self):
        assert OSError in RETRYABLE_EXCEPTIONS


# ---------------------------------------------------------------------------
# PortalFilter
# ---------------------------------------------------------------------------


class TestPortalFilter:
    """Tests for PortalFilter dataclass."""

    def test_default_values(self):
        f = PortalFilter()
        assert f.city is None
        assert f.min_price is None
        assert f.max_price is None
        assert f.min_rooms is None
        assert f.max_rooms is None
        assert f.property_type is None
        assert f.listing_type == "rent"
        assert f.limit == 100

    def test_custom_values(self):
        f = PortalFilter(
            city="Warsaw",
            min_price=1000.0,
            max_price=5000.0,
            min_rooms=2.0,
            max_rooms=4.0,
            property_type="apartment",
            listing_type="sale",
            limit=50,
        )
        assert f.city == "Warsaw"
        assert f.min_price == 1000.0
        assert f.max_price == 5000.0
        assert f.min_rooms == 2.0
        assert f.max_rooms == 4.0
        assert f.property_type == "apartment"
        assert f.listing_type == "sale"
        assert f.limit == 50

    def test_to_dict_filters_none_values(self):
        f = PortalFilter(city="Krakow")
        d = f.to_dict()
        assert "city" in d
        assert d["city"] == "Krakow"
        assert "min_price" not in d
        assert "max_price" not in d

    def test_to_dict_includes_all_non_none(self):
        f = PortalFilter(
            city="Warsaw",
            min_price=500.0,
            max_price=2000.0,
            property_type="apartment",
        )
        d = f.to_dict()
        assert d["city"] == "Warsaw"
        assert d["min_price"] == 500.0
        assert d["max_price"] == 2000.0
        assert d["property_type"] == "apartment"

    def test_to_dict_includes_default_listing_type(self):
        f = PortalFilter()
        d = f.to_dict()
        assert "listing_type" in d
        assert d["listing_type"] == "rent"

    def test_to_dict_includes_default_limit(self):
        f = PortalFilter()
        d = f.to_dict()
        assert "limit" in d
        assert d["limit"] == 100

    def test_to_dict_empty_filter(self):
        f = PortalFilter(listing_type=None, limit=None)
        f.limit = None
        f.listing_type = None
        d = f.to_dict()
        assert d == {}

    def test_str_city_only(self):
        f = PortalFilter(city="Warsaw")
        s = str(f)
        assert "city=Warsaw" in s

    def test_str_price_range(self):
        f = PortalFilter(min_price=500.0, max_price=2000.0)
        s = str(f)
        assert "price=500.0-2000.0" in s

    def test_str_price_min_only(self):
        f = PortalFilter(min_price=500.0)
        s = str(f)
        assert "price=500.0-unlimited" in s

    def test_str_price_max_only(self):
        f = PortalFilter(max_price=2000.0)
        s = str(f)
        assert "price=0-2000.0" in s

    def test_str_rooms_range(self):
        f = PortalFilter(min_rooms=2.0, max_rooms=4.0)
        s = str(f)
        assert "rooms=2.0-4.0" in s

    def test_str_property_type(self):
        f = PortalFilter(property_type="apartment")
        s = str(f)
        assert "type=apartment" in s

    def test_str_listing_type(self):
        f = PortalFilter(listing_type="sale")
        s = str(f)
        assert "listing=sale" in s

    def test_str_no_filters(self):
        f = PortalFilter(listing_type=None, limit=None)
        f.listing_type = None
        s = str(f)
        assert s == "no filters"

    def test_str_all_filters(self):
        f = PortalFilter(
            city="Krakow",
            min_price=500.0,
            max_price=2000.0,
            min_rooms=2.0,
            max_rooms=4.0,
            property_type="apartment",
            listing_type="rent",
        )
        s = str(f)
        assert "city=Krakow" in s
        assert "price=500.0-2000.0" in s
        assert "rooms=2.0-4.0" in s
        assert "type=apartment" in s
        assert "listing=rent" in s


# ---------------------------------------------------------------------------
# PortalFetchResult
# ---------------------------------------------------------------------------


class TestPortalFetchResult:
    """Tests for PortalFetchResult dataclass."""

    def test_default_values(self):
        result = PortalFetchResult(success=True)
        assert result.success is True
        assert result.properties == []
        assert result.count == 0
        assert result.source == ""
        assert result.source_type == "portal"
        assert isinstance(result.fetched_at, datetime)
        assert result.filters is None
        assert result.errors == []
        assert result.metadata == {}

    def test_custom_values(self):
        now = datetime(2024, 1, 1, 12, 0, 0)
        result = PortalFetchResult(
            success=True,
            properties=[{"city": "Warsaw"}],
            count=1,
            source="otodom",
            fetched_at=now,
            errors=["warning1"],
            metadata={"page": 1},
        )
        assert result.count == 1
        assert result.source == "otodom"
        assert result.fetched_at == now

    def test_to_dataframe_with_properties(self):
        result = PortalFetchResult(
            success=True,
            properties=[
                {"city": "Warsaw", "price": 1000},
                {"city": "Krakow", "price": 900},
            ],
            count=2,
        )
        df = result.to_dataframe()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert "city" in df.columns
        assert "price" in df.columns

    def test_to_dataframe_empty_properties(self):
        result = PortalFetchResult(success=False, properties=[])
        df = result.to_dataframe()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    def test_add_error(self):
        result = PortalFetchResult(success=True, source="test_source")
        result.add_error("Something went wrong")
        assert len(result.errors) == 1
        assert result.errors[0] == "Something went wrong"

    def test_add_multiple_errors(self):
        result = PortalFetchResult(success=False, source="test_source")
        result.add_error("Error 1")
        result.add_error("Error 2")
        assert len(result.errors) == 2

    def test_add_error_logs(self, caplog):
        result = PortalFetchResult(success=False, source="test_portal")
        with caplog.at_level("ERROR"):
            result.add_error("test error message")
        assert "test_portal" in caplog.text
        assert "test error message" in caplog.text


# ---------------------------------------------------------------------------
# ExternalSourceAdapter
# ---------------------------------------------------------------------------


class ConcreteAdapter(ExternalSourceAdapter):
    """Concrete implementation for testing the abstract base class."""

    name = "test_portal"
    display_name = "Test Portal"
    requires_api_key = False
    api_key_env_var = "TEST_API_KEY"
    rate_limit_requests = 30
    rate_limit_window = 60

    def fetch(self, filters: PortalFilter) -> PortalFetchResult:
        return PortalFetchResult(success=True, source=self.name, count=0)

    def normalize_property(self, raw_property: dict) -> dict:
        return {"city": raw_property.get("city", "Unknown")}

    def _get_base_url(self) -> str:
        return "https://www.test-portal.example.com"


class KeyRequiredAdapter(ExternalSourceAdapter):
    """Adapter that requires an API key."""

    name = "key_required"
    display_name = "Key Required Portal"
    requires_api_key = True
    api_key_env_var = "REQUIRED_API_KEY"

    def fetch(self, filters: PortalFilter) -> PortalFetchResult:
        return PortalFetchResult(success=True, source=self.name)

    def normalize_property(self, raw_property: dict) -> dict:
        return raw_property

    def _get_base_url(self) -> str:
        return "https://api.key-required.com"


class TestExternalSourceAdapter:
    """Tests for ExternalSourceAdapter abstract base class."""

    def test_concrete_adapter_init(self):
        adapter = ConcreteAdapter()
        assert adapter._api_key is None
        assert adapter.name == "test_portal"

    def test_init_with_api_key(self):
        adapter = ConcreteAdapter(api_key="secret-key-123")
        assert adapter._api_key == "secret-key-123"

    def test_requires_api_key_raises_without_key(self):
        with pytest.raises(ValueError, match="requires API key"):
            KeyRequiredAdapter()

    def test_requires_api_key_succeeds_with_key(self):
        adapter = KeyRequiredAdapter(api_key="my-secret-key")
        assert adapter._api_key == "my-secret-key"

    def test_fetch_returns_result(self):
        adapter = ConcreteAdapter()
        result = adapter.fetch(PortalFilter())
        assert isinstance(result, PortalFetchResult)
        assert result.success is True
        assert result.source == "test_portal"

    def test_normalize_property(self):
        adapter = ConcreteAdapter()
        result = adapter.normalize_property({"city": "Warsaw", "extra": "data"})
        assert result["city"] == "Warsaw"

    def test_normalize_property_missing_city(self):
        adapter = ConcreteAdapter()
        result = adapter.normalize_property({"other": "data"})
        assert result["city"] == "Unknown"

    def test_get_status_without_api_key(self):
        adapter = ConcreteAdapter()
        status = adapter.get_status()
        assert status["name"] == "test_portal"
        assert status["display_name"] == "Test Portal"
        assert status["configured"] is True
        assert status["has_api_key"] is False
        assert status["rate_limit"]["requests"] == 30
        assert status["rate_limit"]["window_seconds"] == 60

    def test_get_status_with_api_key(self):
        adapter = ConcreteAdapter(api_key="key")
        status = adapter.get_status()
        assert status["has_api_key"] is True
        assert status["configured"] is True

    def test_get_status_key_required_configured(self):
        adapter = KeyRequiredAdapter(api_key="key")
        status = adapter.get_status()
        assert status["configured"] is True
        assert status["has_api_key"] is True

    def test_build_source_url_default(self):
        adapter = ConcreteAdapter()
        url = adapter._build_source_url("abc123")
        assert url == "https://www.test-portal.example.com/property/abc123"

    def test_build_source_url_with_path(self):
        adapter = ConcreteAdapter()
        url = adapter._build_source_url("abc123", path="/listing/abc123")
        assert url == "https://www.test-portal.example.com/listing/abc123"

    def test_cannot_instantiate_abstract_class(self):
        with pytest.raises(TypeError):
            ExternalSourceAdapter()

    def test_default_class_attributes(self):
        assert ExternalSourceAdapter.name == ""
        assert ExternalSourceAdapter.display_name == ""
        assert ExternalSourceAdapter.requires_api_key is False
        assert ExternalSourceAdapter.api_key_env_var == ""
        assert ExternalSourceAdapter.rate_limit_requests == 60
        assert ExternalSourceAdapter.rate_limit_window == 60

    def test_validate_configuration_skips_when_no_key_required(self):
        """No error when requires_api_key=False even without API key."""
        adapter = ConcreteAdapter()
        assert adapter._api_key is None  # No error was raised


# ---------------------------------------------------------------------------
# RateLimiter
# ---------------------------------------------------------------------------


class TestRateLimiter:
    """Tests for RateLimiter token bucket implementation."""

    def test_init(self):
        limiter = RateLimiter(requests=10, window=60)
        assert limiter.requests == 10
        assert limiter.window == 60
        assert limiter._tokens == 10

    def test_acquire_returns_true_with_tokens(self):
        limiter = RateLimiter(requests=10, window=60)
        assert limiter.acquire(timeout=1.0) is True
        assert limiter._tokens == 9

    def test_acquire_depletes_tokens(self):
        limiter = RateLimiter(requests=3, window=60)
        assert limiter.acquire(timeout=0.5) is True
        assert limiter.acquire(timeout=0.5) is True
        assert limiter.acquire(timeout=0.5) is True
        # Tokens should be 0 now

    def test_acquire_timeout_when_no_tokens(self):
        """When all tokens are used and no time passes, acquire returns False."""
        limiter = RateLimiter(requests=1, window=3600)  # 1 request per hour
        assert limiter.acquire(timeout=0.1) is True
        # Next acquire should timeout since no tokens refill in short time
        assert limiter.acquire(timeout=0.1) is False

    def test_tokens_refill_over_time(self):
        """Tokens refill based on elapsed time."""
        limiter = RateLimiter(requests=100, window=1)  # 100 per second
        # Use all tokens
        for _ in range(100):
            limiter.acquire(timeout=0.01)
        assert limiter._tokens == 0
        # Wait briefly for tokens to refill
        time.sleep(0.05)
        assert limiter.acquire(timeout=1.0) is True

    def test_reset(self):
        limiter = RateLimiter(requests=5, window=60)
        for _ in range(5):
            limiter.acquire(timeout=0.1)
        assert limiter._tokens == 0
        limiter.reset()
        assert limiter._tokens == 5

    def test_reset_updates_timestamp(self):
        limiter = RateLimiter(requests=5, window=60)
        old_ts = limiter._last_update
        time.sleep(0.01)
        limiter.reset()
        assert limiter._last_update >= old_ts

    def test_acquire_timeout_warning_logged(self, caplog):
        limiter = RateLimiter(requests=1, window=3600)
        limiter.acquire(timeout=0.1)
        with caplog.at_level("WARNING"):
            result = limiter.acquire(timeout=0.1)
        assert result is False
        assert "Rate limiter timeout" in caplog.text

    def test_tokens_capped_at_max(self):
        """Tokens cannot exceed the max requests."""
        limiter = RateLimiter(requests=5, window=60)
        time.sleep(0.1)
        limiter.acquire(timeout=0.1)
        # After refill, tokens should still be <= 5
        assert limiter._tokens <= 5

    def test_acquire_sequential(self):
        """Sequential acquires work within rate limit."""
        limiter = RateLimiter(requests=10, window=1)
        results = [limiter.acquire(timeout=0.5) for _ in range(10)]
        assert all(results)

    def test_refill_rate(self):
        """Token refill rate matches requests/window ratio."""
        # 10 requests per 1 second = 10 tokens/sec
        limiter = RateLimiter(requests=10, window=1)
        # Use all tokens
        for _ in range(10):
            limiter.acquire(timeout=0.01)
        # After 0.1s, should have ~1 token refilled
        time.sleep(0.1)
        # Should be able to acquire at least one
        assert limiter.acquire(timeout=1.0) is True
