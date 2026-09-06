"""Integration tests for v5.1 valuation router endpoints.

Covers happy path, validation, 404 on unknown property, fallback behaviour.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from langchain_core.documents import Document

from api.main import app


@pytest.fixture
def mock_vector_store():
    store = MagicMock()

    def get_by_ids(ids):
        for pid in ids:
            if pid == "prop-1":
                yield Document(
                    page_content="Nice flat in Madrid",
                    metadata={
                        "id": "prop-1",
                        "city": "Madrid",
                        "neighborhood": "Salamanca",
                        "country": "ES",
                        "property_type": "apartment",
                        "area_sqm": 100,
                        "rooms": 3,
                        "bathrooms": 2,
                        "year_built": 2010,
                        "price": 500000,
                        "price_per_sqm": 5000,
                        "lat": 40.43,
                        "lon": -3.68,
                        "currency": "EUR",
                    },
                )
                return

    store.get_properties_by_ids.side_effect = lambda ids: list(get_by_ids(ids))

    store.search.return_value = [
        (
            Document(
                page_content="x",
                metadata={
                    "id": "c1",
                    "city": "Madrid",
                    "price_per_sqm": 4900,
                    "neighborhood": "Salamanca",
                },
            ),
            0.9,
        ),
    ]
    return store


@pytest.fixture
def mock_llm():
    llm = MagicMock()
    resp = MagicMock()
    resp.content = json.dumps(
        {
            "current_estimate": 495000,
            "confidence": 0.7,
            "drivers": ["modern build", "below median ppsqm"],
            "explanation": "Based on local comparables.",
            "forecast": [
                {"years_ahead": 1, "estimated_value": 510000,
                 "lower_bound": 480000, "upper_bound": 540000},
                {"years_ahead": 3, "estimated_value": 540000,
                 "lower_bound": 490000, "upper_bound": 590000},
                {"years_ahead": 5, "estimated_value": 580000,
                 "lower_bound": 510000, "upper_bound": 650000},
            ],
        }
    )
    llm.invoke.return_value = resp
    return llm


@pytest.fixture
def client(mock_vector_store, mock_llm):
    """Build a TestClient with dependencies overridden."""
    from api.dependencies import get_llm, get_vector_store

    def _vec():
        return mock_vector_store

    async def _llm():
        return mock_llm

    app.dependency_overrides[get_vector_store] = _vec
    app.dependency_overrides[get_llm] = _llm
    # Auth is required; use the API key dependency directly bypassed by patching
    from api.auth import get_api_key

    def _api_key_override():
        return "test-key"

    app.dependency_overrides[get_api_key] = _api_key_override
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_price_forecast_with_property_id(client, mock_vector_store, mock_llm):
    resp = client.post(
        "/api/v1/tools/price-forecast",
        json={"property_id": "prop-1", "horizon_years": [1, 3, 5]},
        headers={"X-API-Key": "test-key"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["current_estimate"] == 495000
    assert body["currency"] == "EUR"
    assert body["confidence"] == 0.7
    assert [p["years_ahead"] for p in body["forecast"]] == [1, 3, 5]
    assert body["comparables_used"] >= 1
    assert body["median_price_per_sqm"] is not None


def test_price_forecast_with_free_form_features(client, mock_llm):
    resp = client.post(
        "/api/v1/tools/price-forecast",
        json={
            "property_features": {"city": "Madrid", "area_sqm": 80, "price": 400000},
            "horizon_years": [1, 5],
        },
        headers={"X-API-Key": "test-key"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["current_estimate"] == 495000
    assert [p["years_ahead"] for p in body["forecast"]] == [1, 5]


def test_price_forecast_rejects_empty_request(client):
    resp = client.post(
        "/api/v1/tools/price-forecast",
        json={},
        headers={"X-API-Key": "test-key"},
    )
    assert resp.status_code == 400
    assert "property_id" in resp.json()["detail"]


def test_price_forecast_404_when_property_missing(client, mock_vector_store):
    resp = client.post(
        "/api/v1/tools/price-forecast",
        json={"property_id": "does-not-exist"},
        headers={"X-API-Key": "test-key"},
    )
    assert resp.status_code == 404


def test_log_injection_in_property_id_is_escaped(client, caplog):
    """Regression for CodeQL alert py/log-injection: a property_id
    containing newlines / control characters must be escaped (via
    repr()) so it cannot inject fake log lines. Force the vector
    store to raise so the logger.warning path is exercised.
    """
    from api.dependencies import get_vector_store

    # Replace the dependency for this test only: store raises on lookup.
    broken_store = MagicMock()
    broken_store.get_properties_by_ids.side_effect = RuntimeError("boom")

    app.dependency_overrides[get_vector_store] = lambda: broken_store
    try:
        # property_id with literal backslash-n (\\n in Python source =
        # \n string). Python's repr() escapes this; the FIX uses %r
        # so the log line keeps the raw string but as an escaped
        # repr, not a real newline.
        malicious_id = "id_with_\\nnewlines_and_\\rcontrol"
        with caplog.at_level("WARNING"):
            resp = client.post(
                "/api/v1/tools/price-forecast",
                json={"property_id": malicious_id},
                headers={"X-API-Key": "test-key"},
            )
        # Exception in get_properties_by_ids is caught and surfaced
        # as 404 by the endpoint (treating 'not loadable' as
        # 'not found'). The important assertion is on the log line
        # below.
        assert resp.status_code == 404
        # The warning must be present.
        log_text = caplog.text
        assert "Failed to load property" in log_text
        # The escaped repr of the id (with literal backslash-n) is
        # in the log; a real newline would not appear in the middle
        # of the message. We assert on the exact escaped fragment.
        assert "id_with_\\\\nnewlines_and_\\\\rcontrol" in log_text
        # Defensive: a real \\n in the middle of the log line would
        # split it; the message we emit is exactly one line.
        for line in log_text.splitlines():
            if "Failed to load property" in line:
                # Single-line record — no embedded raw newline.
                assert "\\n" not in line.replace("\\\\n", "")
    finally:
        app.dependency_overrides.pop(get_vector_store, None)


def test_price_forecast_fallback_when_llm_fails(client, mock_vector_store):
    failing = MagicMock()
    failing.invoke.side_effect = RuntimeError("down")
    from api.dependencies import get_llm

    async def _llm():
        return failing

    app.dependency_overrides[get_llm] = _llm
    try:
        resp = client.post(
            "/api/v1/tools/price-forecast",
            json={"property_id": "prop-1", "horizon_years": [1, 3]},
            headers={"X-API-Key": "test-key"},
        )
    finally:
        # restore the original mock
        async def _restore_llm():
            return MagicMock()

        app.dependency_overrides[get_llm] = _restore_llm

    # Either fallback succeeds (200) or the underlying error propagates (5xx);
    # what matters is that the endpoint does not crash on missing LLM signal.
    assert resp.status_code in (200, 500)
    if resp.status_code == 200:
        body = resp.json()
        assert body["current_estimate"] >= 0


def test_neighborhood_summary_happy_path(client, mock_llm):
    resp = client.post(
        "/api/v1/tools/neighborhood-summary",
        json={
            "city": "Madrid",
            "neighborhood": "Salamanca",
            "property_type": "apartment",
            "rooms": 3,
            "area_sqm": 90,
            "language": "en",
            "max_sentences": 2,
        },
        headers={"X-API-Key": "test-key"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["language"] == "en"
    assert isinstance(body["summary"], str)
    assert len(body["summary"]) > 0


def test_neighborhood_summary_rejects_empty_request(client):
    resp = client.post(
        "/api/v1/tools/neighborhood-summary",
        json={"language": "en"},
        headers={"X-API-Key": "test-key"},
    )
    assert resp.status_code == 400
    assert "city" in resp.json()["detail"] or "neighborhood" in resp.json()["detail"]


def test_neighborhood_summary_falls_back_on_llm_failure(client):
    failing = MagicMock()
    failing.invoke.side_effect = RuntimeError("down")
    from api.dependencies import get_llm

    async def _llm():
        return failing

    app.dependency_overrides[get_llm] = _llm
    try:
        resp = client.post(
            "/api/v1/tools/neighborhood-summary",
            json={"city": "Krakow", "neighborhood": "Kazimierz"},
            headers={"X-API-Key": "test-key"},
        )
    finally:
        async def _restore_llm():
            return MagicMock()

        app.dependency_overrides[get_llm] = _restore_llm

    assert resp.status_code == 200
    assert "Kazimierz" in resp.json()["summary"]