from time import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from api.main import app, shutdown_event, startup_event


class _DummyScheduler:
    def __init__(self, *args, **kwargs):
        self.started = False
        self.stopped = False

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True


@pytest.mark.asyncio
async def test_startup_initializes_scheduler(monkeypatch):
    # Patch names used inside api.main
    import api.main as main_mod

    monkeypatch.setattr(
        main_mod, "EmailServiceFactory", SimpleNamespace(create_from_env=lambda: None)
    )
    monkeypatch.setattr(main_mod, "NotificationScheduler", _DummyScheduler)
    monkeypatch.setattr(main_mod, "get_vector_store", lambda: None)

    await startup_event()

    assert isinstance(getattr(app.state, "scheduler", None), _DummyScheduler)
    assert app.state.scheduler.started is True


@pytest.mark.asyncio
async def test_shutdown_stops_scheduler(monkeypatch):
    # Ensure scheduler exists
    from api import main as main_mod

    main_mod.scheduler = _DummyScheduler()
    app.state.scheduler = main_mod.scheduler
    await shutdown_event()
    assert main_mod.scheduler.stopped is True


class TestTask17Features:
    """Tests for TASK-017 Production Deployment Optimization features."""

    @pytest.mark.asyncio
    async def test_startup_initializes_response_cache(monkeypatch):
        """Test that startup initializes ResponseCache (TASK-017)."""
        import api.main as main_mod

        # Mock dependencies using setattr on module
        main_mod.EmailServiceFactory = SimpleNamespace(create_from_env=lambda: None)
        main_mod.NotificationScheduler = _DummyScheduler
        main_mod.get_vector_store = lambda: None

        await startup_event()

        # Verify response_cache is initialized
        assert hasattr(app.state, "response_cache")
        assert hasattr(app.state, "start_time")
        assert isinstance(app.state.start_time, float)

    @pytest.mark.asyncio
    async def test_startup_initializes_connection_pool_manager(monkeypatch):
        """Test that startup initializes ConnectionPoolManager (TASK-017)."""
        import api.main as main_mod

        # Mock dependencies using setattr on module
        main_mod.EmailServiceFactory = SimpleNamespace(create_from_env=lambda: None)
        main_mod.NotificationScheduler = _DummyScheduler
        main_mod.get_vector_store = lambda: None

        await startup_event()

        # Verify pool_manager is initialized
        assert hasattr(app.state, "pool_manager")

    @pytest.mark.asyncio
    async def test_shutdown_clears_response_cache(monkeypatch):
        """Test that shutdown clears ResponseCache (TASK-017)."""
        import api.main as main_mod

        # Mock scheduler
        main_mod.scheduler = _DummyScheduler()
        app.state.scheduler = main_mod.scheduler

        # Create a mock response_cache with async clear_all
        mock_cache = MagicMock()
        mock_cache.clear_all = AsyncMock()
        app.state.response_cache = mock_cache

        await shutdown_event()

        # Verify clear_all was called
        mock_cache.clear_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_closes_connection_pools(monkeypatch):
        """Test that shutdown closes connection pools (TASK-017)."""
        import api.main as main_mod

        # Mock scheduler
        main_mod.scheduler = _DummyScheduler()
        app.state.scheduler = main_mod.scheduler

        # Create a mock pool_manager with async close_all
        mock_pool_manager = MagicMock()
        mock_pool_manager.close_all = AsyncMock()
        app.state.pool_manager = mock_pool_manager

        await shutdown_event()

        # Verify close_all was called
        mock_pool_manager.close_all.assert_called_once()


class TestMetricsEndpoint:
    """Tests for the metrics endpoint (TASK-017)."""

    @pytest.mark.asyncio
    async def test_metrics_endpoint_returns_prometheus_format(monkeypatch):
        """Test that metrics endpoint returns Prometheus text format."""
        from api.main import metrics_endpoint

        # Set up app state with required attributes
        app.state.start_time = time() - 100  # 100 seconds uptime
        app.state.metrics = {"GET /api/v1/health": 5, "POST /api/v1/search": 3}

        # Set up mock response_cache
        mock_cache = MagicMock()
        mock_cache.get_stats.return_value = {
            "enabled": True,
            "size": 42,
            "backend": "memory",
        }
        app.state.response_cache = mock_cache

        # Call endpoint
        result = await metrics_endpoint()

        # Verify response
        if isinstance(result, tuple):
            body, status_code, headers = result
        else:
            body = result
            status_code = 200
            headers = {}

        assert status_code == 200
        assert "text/plain" in headers.get("Content-Type", "")

        # Verify Prometheus format in body
        assert "# HELP" in body
        assert "# TYPE" in body
        assert "api_requests_total" in body
        assert "api_cache_size" in body
        assert "api_uptime_seconds" in body

    @pytest.mark.asyncio
    async def test_metrics_endpoint_without_cache(monkeypatch):
        """Test metrics endpoint when cache is not configured."""
        from api.main import metrics_endpoint

        # Set up minimal app state
        app.state.start_time = time() - 50

        # Remove response_cache
        if hasattr(app.state, "response_cache"):
            delattr(app.state, "response_cache")

        result = await metrics_endpoint()

        # Should still work without cache
        body = result[0] if isinstance(result, tuple) else result
        assert "api_uptime_seconds" in body
