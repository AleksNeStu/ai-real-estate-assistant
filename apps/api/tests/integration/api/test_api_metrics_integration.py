import pytest
from fastapi.testclient import TestClient

from api.main import app
from config.settings import get_settings


@pytest.fixture(autouse=True)
def _open_the_admin_gate(open_admin_gate):
    """These tests exercise the handlers behind the gate, not the gate."""


def test_metrics_counts_increment():
    client = TestClient(app)
    settings = get_settings()
    headers = {"X-API-Key": settings.api_access_key}

    r0 = client.get("/api/v1/admin/metrics", headers=headers)
    assert r0.status_code == 200
    baseline = r0.json().get("requests", {}).get("GET /api/v1/verify-auth", 0)

    r1 = client.get("/api/v1/verify-auth", headers=headers)
    assert r1.status_code == 200
    r2 = client.get("/api/v1/verify-auth", headers=headers)
    assert r2.status_code == 200

    r_metrics = client.get("/api/v1/admin/metrics", headers=headers)
    assert r_metrics.status_code == 200
    data = r_metrics.json()
    assert data.get("requests", {}).get("GET /api/v1/verify-auth", 0) - baseline == 2
