"""Tests for the /health route family.

`/health` is the stable, no-auth monitoring probe (Render's healthCheckPath and
the Dockerfile HEALTHCHECK both target it). The comprehensive payload that used
to shadow it was moved to `/health/detailed`.

These tests pin both halves of that contract so a future re-registration of a
second `/health` handler cannot silently make the rich payload unreachable
again (see F-20260903 route collision in the monitoring router).
"""

import pytest
from fastapi.testclient import TestClient

from api.health import DependencyHealth, HealthCheckResponse, HealthStatus


def _iter_route_paths(routes, prefix: str = ""):
    """Yield ``(path, methods)`` for every route, flattening included routers.

    Recent FastAPI versions nest ``include_router`` results behind an
    ``_IncludedRouter`` wrapper instead of copying the routes onto the app, so
    a flat scan of ``app.routes`` misses everything registered via a router.
    """
    for route in routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None)
        if path is not None and methods:
            yield prefix + path, methods
            continue

        original = getattr(route, "original_router", None)
        context = getattr(route, "include_context", None)
        if original is not None and context is not None:
            yield from _iter_route_paths(
                original.routes, prefix + (getattr(context, "prefix", None) or "")
            )


@pytest.fixture
def mock_health_status(monkeypatch):
    """Patch the health aggregator used by the /health/detailed handler."""

    def _mock(status: HealthStatus = HealthStatus.HEALTHY):
        response = HealthCheckResponse(
            status=status,
            version="1.2.3",
            timestamp="2026-01-01T00:00:00Z",
            dependencies={
                "vector_store": DependencyHealth(
                    name="vector_store",
                    status=HealthStatus.HEALTHY,
                    message="OK",
                ),
            },
            uptime_seconds=42.0,
        )

        async def _fake_get_health_status(*_args, **_kwargs):
            return response

        monkeypatch.setattr("api.main.get_health_status", _fake_get_health_status)
        return response

    return _mock


class TestHealthProbeShape:
    """`/health` must stay the stable monitoring shape."""

    def test_health_returns_monitoring_shape(self):
        """`/health` returns status/timestamp/service and no dependency payload."""
        from api.main import app

        with TestClient(app) as client:
            response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "ai-real-estate-assistant"
        assert "timestamp" in data
        # The monitoring shape deliberately omits the heavyweight payload.
        assert "dependencies" not in data
        assert "uptime_seconds" not in data
        assert "version" not in data

    def test_health_requires_no_auth(self):
        """`/health` is reachable without an API key (infrastructure probe)."""
        from api.main import app

        with TestClient(app) as client:
            response = client.get("/health")

        assert response.status_code == 200

    def test_health_is_registered_exactly_once(self):
        """Only one handler may answer `/health` — the monitoring one."""
        from api.main import app

        health_routes = [
            path
            for path, methods in _iter_route_paths(app.routes)
            if path == "/health" and "GET" in methods
        ]

        assert len(health_routes) == 1, (
            f"expected exactly one GET /health route, found {len(health_routes)}. "
            "A second registration would shadow the monitoring probe at runtime "
            "(FastAPI resolves the first match)."
        )


class TestHealthDetailed:
    """`/health/detailed` exposes the comprehensive payload."""

    def test_health_detailed_returns_rich_payload(self, mock_health_status):
        """`/health/detailed` returns version, uptime and dependency details."""
        from api.main import app

        mock_health_status(HealthStatus.HEALTHY)

        with TestClient(app) as client:
            response = client.get("/health/detailed")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "1.2.3"
        assert data["uptime_seconds"] == 42.0
        assert "timestamp" in data
        assert "dependencies" in data
        assert data["dependencies"]["vector_store"]["status"] == "healthy"

    def test_health_detailed_returns_503_when_unhealthy(self, mock_health_status):
        """An unhealthy aggregate still surfaces its dependency detail."""
        from api.main import app

        mock_health_status(HealthStatus.UNHEALTHY)

        with TestClient(app) as client:
            response = client.get("/health/detailed")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert "dependencies" in data

    def test_health_detailed_is_distinct_from_health(self, mock_health_status):
        """The two endpoints must not return the same payload shape."""
        from api.main import app

        mock_health_status(HealthStatus.HEALTHY)

        with TestClient(app) as client:
            probe = client.get("/health").json()
            detailed = client.get("/health/detailed").json()

        assert set(probe) != set(detailed)
        assert "dependencies" in detailed
        assert "dependencies" not in probe


class TestHealthRouteFamily:
    """The whole `/health/*` family stays reachable."""

    def test_health_family_routes_are_registered(self):
        """`/health`, `/health/detailed`, `/health/ready` and `/health/live` exist."""
        from api.main import app

        paths = {path for path, _methods in _iter_route_paths(app.routes)}

        assert "/health" in paths
        assert "/health/detailed" in paths
        assert "/health/ready" in paths
        assert "/health/live" in paths

    def test_health_detailed_is_not_shadowed(self):
        """`/health/detailed` must be the only handler serving that path.

        A second registration would make the rich payload unreachable at
        runtime while still appearing in the OpenAPI schema, which is exactly
        how the original `/health` collision went unnoticed.
        """
        from api.main import app

        detailed_routes = [
            path
            for path, methods in _iter_route_paths(app.routes)
            if path == "/health/detailed" and "GET" in methods
        ]

        assert len(detailed_routes) == 1, (
            f"expected exactly one GET /health/detailed route, found {len(detailed_routes)}"
        )
