"""Unit tests for K8s health endpoints (/health/ready, /health/live)."""

import pytest
from fastapi.testclient import TestClient

from api.health import DependencyHealth, HealthCheckResponse, HealthStatus


@pytest.fixture
def mock_health_status(monkeypatch):
    """Fixture to mock get_health_status."""

    def _mock(status: HealthStatus, vector_store_status: HealthStatus = HealthStatus.HEALTHY):
        response = HealthCheckResponse(
            status=status,
            version="1.0.0",
            timestamp="2026-01-01T00:00:00Z",
            dependencies={
                "vector_store": DependencyHealth(
                    name="vector_store",
                    status=vector_store_status,
                    message="OK" if vector_store_status == HealthStatus.HEALTHY else "Error",
                ),
            },
            uptime_seconds=100.0,
        )

        async def _fake_get_health_status(*_args, **_kwargs):
            return response

        monkeypatch.setattr("api.main.get_health_status", _fake_get_health_status)
        return response

    return _mock


class TestHealthReadyEndpoint:
    """Tests for /health/ready endpoint."""

    @pytest.mark.asyncio
    async def test_health_ready_returns_200_when_healthy(self, mock_health_status):
        """Readiness probe returns 200 when vector store is healthy."""
        from api.main import app

        mock_health_status(HealthStatus.HEALTHY, HealthStatus.HEALTHY)

        with TestClient(app) as client:
            response = client.get("/health/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"

    @pytest.mark.asyncio
    async def test_health_ready_returns_503_when_vector_store_unhealthy(self, mock_health_status):
        """Readiness probe returns 503 when vector store is unhealthy."""
        from api.main import app

        mock_health_status(HealthStatus.UNHEALTHY, HealthStatus.UNHEALTHY)

        with TestClient(app) as client:
            response = client.get("/health/ready")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert "vector_store" in data["reason"]

    @pytest.mark.asyncio
    async def test_health_ready_returns_200_when_degraded(self, mock_health_status):
        """Readiness probe returns 200 when system is degraded but functional."""
        from api.main import app

        mock_health_status(HealthStatus.DEGRADED, HealthStatus.HEALTHY)

        with TestClient(app) as client:
            response = client.get("/health/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"


class TestHealthLiveEndpoint:
    """Tests for /health/live endpoint."""

    @pytest.mark.asyncio
    async def test_health_live_returns_200(self):
        """Liveness probe always returns 200."""
        from api.main import app

        with TestClient(app) as client:
            response = client.get("/health/live")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_health_live_includes_timestamp(self):
        """Liveness probe includes current timestamp."""
        from api.main import app

        with TestClient(app) as client:
            response = client.get("/health/live")

        data = response.json()
        assert "timestamp" in data
        # Timestamp should be ISO format
        assert "T" in data["timestamp"]
