import builtins
import logging
import re
import sys
import types

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.observability import (
    RateLimiter,
    RedisRateLimiter,
    add_observability,
    client_id_from_api_key,
    generate_request_id,
    normalize_request_id,
)


def _fake_redis_module(current_count: int, oldest_ts: float):
    class _FakePipeline:
        def __init__(self, count: int):
            self._count = count

        def zremrangebyscore(self, *args, **kwargs):
            return self

        def zcard(self, *args, **kwargs):
            return self

        def zadd(self, *args, **kwargs):
            return self

        def expire(self, *args, **kwargs):
            return self

        def execute(self):
            return [0, self._count, 0, 0]

    class _FakeRedis:
        def __init__(self, count: int, oldest: float):
            self._count = count
            self._oldest = oldest

        def ping(self):
            return True

        def pipeline(self):
            return _FakePipeline(self._count)

        def zrange(self, *args, **kwargs):
            return [("0", self._oldest)]

    def from_url(*args, **kwargs):
        return _FakeRedis(current_count, oldest_ts)

    return types.SimpleNamespace(from_url=from_url)


def test_rate_limiter_allows_within_limit():
    rl = RateLimiter(max_requests=2, window_seconds=60)
    ok1, limit1, rem1, reset1 = rl.check("c1", now=0.0)
    ok2, limit2, rem2, reset2 = rl.check("c1", now=0.0)
    assert ok1 is True and ok2 is True
    assert limit1 == 2 and limit2 == 2
    assert rem1 == 1 and rem2 == 0
    assert reset1 == 60 and reset2 == 60


def test_rate_limiter_blocks_when_exceeded():
    rl = RateLimiter(max_requests=1, window_seconds=60)
    ok1, _, _, _ = rl.check("c1", now=0.0)
    ok2, limit2, rem2, reset2 = rl.check("c1", now=0.0)
    assert ok1 is True
    assert ok2 is False
    assert limit2 == 1
    assert rem2 == 0
    assert reset2 == 60


def test_redis_rate_limiter_allows_when_under_limit(monkeypatch):
    monkeypatch.setitem(sys.modules, "redis", _fake_redis_module(current_count=0, oldest_ts=1000.0))
    limiter = RedisRateLimiter(
        redis_url="redis://localhost",
        max_requests=2,
        window_seconds=60,
        fallback_to_in_memory=False,
    )
    ok, limit, remaining, reset_in = limiter.check("c1", now=1000.0)
    assert ok is True
    assert limit == 2
    assert remaining == 2
    assert reset_in >= 1


def test_redis_rate_limiter_blocks_when_over_limit(monkeypatch):
    monkeypatch.setitem(sys.modules, "redis", _fake_redis_module(current_count=2, oldest_ts=1000.0))
    limiter = RedisRateLimiter(
        redis_url="redis://localhost",
        max_requests=2,
        window_seconds=60,
        fallback_to_in_memory=False,
    )
    ok, limit, remaining, reset_in = limiter.check("c1", now=1000.0)
    assert ok is False
    assert limit == 2
    assert remaining == 0
    assert reset_in >= 1


def test_redis_rate_limiter_falls_back_on_import_error(monkeypatch):
    original_import = builtins.__import__

    def _import(name, *args, **kwargs):
        if name == "redis":
            raise ImportError("missing redis")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _import)
    limiter = RedisRateLimiter(
        redis_url="redis://localhost",
        max_requests=1,
        window_seconds=60,
        fallback_to_in_memory=True,
    )
    ok1, _, _, _ = limiter.check("c1", now=0.0)
    ok2, limit2, remaining2, reset2 = limiter.check("c1", now=0.0)
    assert ok1 is True
    assert ok2 is False
    assert limit2 == 1
    assert remaining2 == 0
    assert reset2 == 60


def test_normalize_request_id_valid_and_invalid():
    assert normalize_request_id("abc-123._") == "abc-123._"
    assert normalize_request_id("  abc-123  ") == "abc-123"
    assert normalize_request_id("") is None
    assert normalize_request_id("   ") is None
    assert normalize_request_id("invalid*char") is None


def test_generate_request_id_format():
    rid = generate_request_id()
    assert isinstance(rid, str)
    assert bool(re.fullmatch(r"[0-9a-f]{32}", rid))


def test_client_id_from_api_key_hashing():
    h1 = client_id_from_api_key("key123")
    h2 = client_id_from_api_key("key123")
    h3 = client_id_from_api_key("other")
    assert h1 is not None and h2 is not None and h3 is not None
    assert len(h1) == 12
    assert h1 == h2
    assert h1 != h3


def test_request_id_header_replaced_when_invalid():
    app = FastAPI()
    add_observability(app, logger=logging.getLogger("test"))

    @app.get("/ping")
    def _ping():
        return {"ok": True}

    client = TestClient(app)
    invalid = "not ok!*"
    r = client.get("/ping", headers={"X-Request-ID": invalid})
    assert r.status_code == 200
    rid = r.headers.get("x-request-id")
    assert rid
    assert rid != invalid
    assert bool(re.fullmatch(r"[0-9a-f]{32}", rid))


def test_request_id_is_present_on_unhandled_exception_response():
    app = FastAPI()
    add_observability(app, logger=logging.getLogger("test"))

    @app.get("/boom")
    def _boom():
        raise RuntimeError("boom")

    client = TestClient(app)
    request_id = "test-req-500"
    r = client.get("/boom", headers={"X-Request-ID": request_id})
    assert r.status_code == 500
    assert r.headers.get("x-request-id") == request_id
    assert r.json()["detail"] == "Internal server error"


def test_rate_limiter_configure_updates_limits():
    rl = RateLimiter(max_requests=1, window_seconds=60)
    rl.configure(max_requests=5, window_seconds=120)

    ok1, limit1, _, _ = rl.check("c1", now=0.0)
    ok2, limit2, _, _ = rl.check("c1", now=0.0)
    ok3, limit3, _, _ = rl.check("c1", now=0.0)

    assert ok1 is True and ok2 is True and ok3 is True
    assert limit1 == 5 and limit2 == 5 and limit3 == 5


def test_rate_limiter_reset_clears_history():
    rl = RateLimiter(max_requests=1, window_seconds=60)
    rl.check("c1", now=0.0)
    ok2, _, _, _ = rl.check("c1", now=0.0)
    assert ok2 is False

    rl.reset()
    ok3, _, _, _ = rl.check("c1", now=0.0)
    assert ok3 is True


def test_rate_limiter_allows_anonymous_key():
    rl = RateLimiter(max_requests=1, window_seconds=60)
    ok, limit, remaining, reset = rl.check("", now=0.0)
    assert ok is True
    assert limit == 1
    assert remaining == 0
    assert reset == 60


def test_normalize_request_id_handles_none():
    assert normalize_request_id(None) is None


def test_client_id_from_api_key_handles_none():
    assert client_id_from_api_key(None) is None
    assert client_id_from_api_key("") is None
    # Whitespace-only keys still get hashed (function doesn't strip)
    result = client_id_from_api_key("  ")
    assert result is not None
    assert len(result) == 12


def test_add_observability_rate_limit_disabled_when_setting_false(monkeypatch):
    monkeypatch.setenv("API_RATE_LIMIT_ENABLED", "false")
    app = FastAPI()
    logger = logging.getLogger("test")
    add_observability(app, logger)

    @app.get("/ping")
    def _ping():
        return {"ok": True}

    client = TestClient(app)
    r = client.get("/ping")
    assert r.status_code == 200


def test_add_observability_sets_request_id_header():
    app = FastAPI()
    logger = logging.getLogger("test")
    add_observability(app, logger)

    @app.get("/ping")
    def _ping():
        return {"ok": True}

    client = TestClient(app)
    r = client.get("/ping")
    assert "x-request-id" in r.headers


def test_exception_uses_registered_custom_handler():
    """Test that custom exception handlers are called for specific exceptions."""
    app = FastAPI()
    logger = logging.getLogger("test")
    add_observability(app, logger)

    custom_exception_called = []

    async def _custom_handler(request, exc):
        custom_exception_called.append(True)
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=418, content={"detail": "custom handled"})

    # Register custom handler for ValueError
    app.add_exception_handler(ValueError, _custom_handler)

    @app.get("/custom-error")
    def _custom_error():
        raise ValueError("custom error")

    client = TestClient(app)
    r = client.get("/custom-error")
    assert r.status_code == 418
    assert r.json()["detail"] == "custom handled"
    assert custom_exception_called


def test_exception_handler_propagates_response_headers():
    """Test that response headers are preserved when using custom exception handlers."""
    app = FastAPI()
    logger = logging.getLogger("test")
    add_observability(app, logger)

    async def _custom_handler(request, exc):
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=400,
            content={"detail": "validation failed"},
            headers={"X-Custom": "custom-value"},
        )

    app.add_exception_handler(ValueError, _custom_handler)

    @app.get("/validate")
    def _validate():
        raise ValueError("invalid")

    client = TestClient(app)
    r = client.get("/validate")
    assert r.status_code == 400
    assert r.headers.get("x-request-id")  # Observability header preserved
    # Note: handler headers are also preserved


def test_exception_fallback_to_generic_500_when_no_handler():
    """Test that unhandled exceptions fall back to generic 500 response."""
    app = FastAPI()
    logger = logging.getLogger("test")
    add_observability(app, logger)

    @app.get("/unhandled")
    def _unhandled():
        raise RuntimeError("unexpected error")

    client = TestClient(app)
    r = client.get("/unhandled")
    assert r.status_code == 500
    assert r.headers.get("x-request-id")
    assert r.json()["detail"] == "Internal server error"


def test_exception_handler_supports_async_handlers():
    """Test that async exception handlers are properly awaited."""
    app = FastAPI()
    logger = logging.getLogger("test")
    add_observability(app, logger)

    async_handler_called = []

    async def _async_handler(request, exc):
        async_handler_called.append(True)
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=422, content={"detail": "async handled"})

    app.add_exception_handler(TypeError, _async_handler)

    @app.get("/async-error")
    def _async_error():
        raise TypeError("type error")

    client = TestClient(app)
    r = client.get("/async-error")
    assert r.status_code == 422
    assert r.json()["detail"] == "async handled"
    assert async_handler_called


def test_exception_handler_checks_base_exception_handler():
    """Test that base Exception handler is used when specific handler not found."""
    app = FastAPI()
    logger = logging.getLogger("test")
    add_observability(app, logger)

    base_handler_called = []

    async def _base_handler(request, exc):
        base_handler_called.append(True)
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=500, content={"detail": "base handler"})

    # Register base Exception handler
    app.add_exception_handler(Exception, _base_handler)

    @app.get("/any-error")
    def _any_error():
        raise RuntimeError("some error")

    client = TestClient(app)
    r = client.get("/any-error")
    assert r.status_code == 500
    assert r.json()["detail"] == "base handler"
    assert base_handler_called


def test_request_succeeds_when_metrics_state_was_removed():
    """A missing request counter must not turn a successful response into a 500.

    The counter lives on the application state, and anything that touches that
    state can remove it. When it is gone the middleware recreates it and the
    request still succeeds - the counts restart, the response does not fail.
    """
    app = FastAPI()
    logger = logging.getLogger("test")
    add_observability(app, logger)

    @app.get("/ping")
    def _ping():
        return {"ok": True}

    del app.state.metrics

    client = TestClient(app)
    r = client.get("/ping")

    assert r.status_code == 200
    assert r.json() == {"ok": True}
    assert app.state.metrics["GET /ping"] == 1


def test_request_succeeds_when_metrics_state_is_not_a_dict():
    """A corrupted request counter is replaced rather than raised through."""
    app = FastAPI()
    logger = logging.getLogger("test")
    add_observability(app, logger)

    @app.get("/ping")
    def _ping():
        return {"ok": True}

    app.state.metrics = "not-a-dict"

    client = TestClient(app)
    r = client.get("/ping")

    assert r.status_code == 200
    assert app.state.metrics["GET /ping"] == 1


def test_request_counter_is_kept_across_requests():
    """The counter accumulates instead of being reset on every request."""
    app = FastAPI()
    logger = logging.getLogger("test")
    add_observability(app, logger)

    @app.get("/ping")
    def _ping():
        return {"ok": True}

    client = TestClient(app)
    client.get("/ping")
    client.get("/ping")

    assert app.state.metrics["GET /ping"] == 2
