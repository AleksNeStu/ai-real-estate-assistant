def test_uptime_monitor_starts_with_env(monkeypatch):
    TestClient = __import__("fastapi.testclient", fromlist=["TestClient"]).TestClient
    app = __import__("api.main", fromlist=["app"]).app

    monkeypatch.setenv("UPTIME_MONITOR_ENABLED", "true")
    monkeypatch.setenv("UPTIME_MONITOR_EMAIL_TO", "ops@example.com")
    monkeypatch.setenv("UPTIME_MONITOR_HEALTH_URL", "http://localhost:8000/health")
    with TestClient(app) as client:
        assert hasattr(app.state, "uptime_monitor")
        assert app.state.uptime_monitor is not None
        resp = client.get("/health")
        assert resp.status_code == 200
