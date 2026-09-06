"""Unit tests for the v5.1 PriceForecastTool.

LLM is always mocked so tests are deterministic and provider-free.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from tools.price_forecast_tools import (
    PriceForecastResult,
    PriceForecastTool,
)


def _llm_with_response(payload: dict) -> MagicMock:
    """Build a MagicMock LLM whose .invoke() returns the given JSON payload."""
    llm = MagicMock()
    response = MagicMock()
    response.content = json.dumps(payload)
    llm.invoke.return_value = response
    return llm


def _tool_with_llm(payload: dict, vector_store: MagicMock | None = None) -> PriceForecastTool:
    tool = PriceForecastTool(vector_store=vector_store)
    tool._llm = _llm_with_response(payload)  # type: ignore[assignment]
    return tool


def test_sanitize_horizon_filters_out_of_range_and_dedupes():
    out = PriceForecastTool._sanitize_horizon([0, 1, 3, 11, 3, "two", 5])
    assert out == [1, 3, 5]


def test_sanitize_horizon_defaults_when_empty():
    assert PriceForecastTool._sanitize_horizon([]) == [1, 3, 5]
    assert PriceForecastTool._sanitize_horizon(None) == [1, 3, 5]  # type: ignore[arg-type]


def test_coerce_features_merges_id_and_dict():
    args = {"property_id": "p1", "property_features": {"city": "Madrid"}}
    feats = PriceForecastTool._coerce_features(args)
    assert feats["id"] == "p1"
    assert feats["city"] == "Madrid"


def test_extract_comparables_returns_empty_without_vector_store():
    assert PriceForecastTool._extract_comparables(None, {"city": "Madrid"}) == []


def test_extract_comparables_parses_vector_store_results():
    from langchain_core.documents import Document

    store = MagicMock()
    store.search.return_value = [
        (
            Document(
                page_content="x",
                metadata={
                    "id": "p1",
                    "city": "Madrid",
                    "price": 500000,
                    "price_per_sqm": 5000,
                    "area_sqm": 100,
                },
            ),
            0.9,
        ),
    ]
    out = PriceForecastTool._extract_comparables(
        store, {"city": "Madrid", "area_sqm": 100, "rooms": 3}
    )
    assert len(out) == 1
    assert out[0]["id"] == "p1"
    assert out[0]["price_per_sqm"] == 5000


def test_median_price_per_sqm():
    comps = [{"price_per_sqm": 5000}, {"price_per_sqm": 6000}, {"price_per_sqm": 7000}]
    assert PriceForecastTool._median_price_per_sqm(comps) == 6000


def test_neighborhood_median_filters_by_neighborhood():
    comps = [
        {"price_per_sqm": 5000, "neighborhood": "Centro"},
        {"price_per_sqm": 7000, "neighborhood": "Salamanca"},
        {"price_per_sqm": 8000, "neighborhood": "Salamanca"},
    ]
    assert (
        PriceForecastTool._neighborhood_median_price_per_sqm(comps, "Salamanca")
        == 7500
    )


def test_build_fallback_uses_anchor_ppsm_when_present():
    res = PriceForecastTool._build_fallback(
        {"area_sqm": 100, "currency": "EUR"},
        [1, 5],
        median_ppsm=5000,
        nbh_median_ppsm=None,
        n_comps=5,
    )
    assert isinstance(res, PriceForecastResult)
    assert res.current_estimate == 500000
    assert len(res.forecast) == 2
    assert res.forecast[0].years_ahead == 1
    # 3%/yr compound from 500k: 500k -> ~515k (yr1), 500k -> ~579.6k (yr5)
    assert 514000 <= res.forecast[0].estimated_value <= 516000
    assert 575000 <= res.forecast[1].estimated_value <= 585000
    assert res.confidence >= 0.3


def test_build_fallback_uses_asking_when_no_anchor():
    res = PriceForecastTool._build_fallback(
        {"price": 250000},
        [3],
        median_ppsm=None,
        nbh_median_ppsm=None,
        n_comps=0,
    )
    assert res.current_estimate == 250000
    assert res.confidence == 0.2


def test_forecast_happy_path():
    payload = {
        "current_estimate": 480000,
        "confidence": 0.7,
        "drivers": ["good transport", "modern build", "below median ppsqm"],
        "explanation": "Solid estimate based on local comparables.",
        "forecast": [
            {"years_ahead": 1, "estimated_value": 495000,
             "lower_bound": 470000, "upper_bound": 520000},
            {"years_ahead": 3, "estimated_value": 525000,
             "lower_bound": 480000, "upper_bound": 570000},
            {"years_ahead": 5, "estimated_value": 560000,
             "lower_bound": 500000, "upper_bound": 620000},
        ],
    }
    tool = _tool_with_llm(payload)
    res = tool.forecast(
        {
            "property_id": None,
            "property_features": {"city": "Madrid", "area_sqm": 100},
            "horizon_years": [1, 3, 5],
        }
    )
    assert res.current_estimate == 480000
    assert res.confidence == 0.7
    assert len(res.forecast) == 3
    assert res.forecast[2].years_ahead == 5
    assert res.forecast[2].estimated_value == 560000
    assert len(res.drivers) == 3


def test_forecast_drops_unrequested_horizons():
    payload = {
        "current_estimate": 100000,
        "forecast": [
            {"years_ahead": 1, "estimated_value": 103000,
             "lower_bound": 100000, "upper_bound": 106000},
            {"years_ahead": 5, "estimated_value": 116000,
             "lower_bound": 110000, "upper_bound": 122000},
            {"years_ahead": 10, "estimated_value": 134000,
             "lower_bound": 120000, "upper_bound": 148000},
        ],
        "confidence": 0.5,
        "drivers": ["x"],
        "explanation": "y",
    }
    tool = _tool_with_llm(payload)
    res = tool.forecast(
        {
            "property_features": {"area_sqm": 50, "price": 100000},
            "horizon_years": [1, 5],
        }
    )
    assert [p.years_ahead for p in res.forecast] == [1, 5]
    assert all(p.estimated_value > 0 for p in res.forecast)


def test_forecast_llm_failure_uses_fallback():
    llm = MagicMock()
    llm.invoke.side_effect = RuntimeError("provider down")
    tool = PriceForecastTool(vector_store=None)
    tool._llm = llm  # type: ignore[assignment]
    res = tool.forecast(
        {
            "property_features": {"price": 200000, "area_sqm": 80},
            "horizon_years": [3],
        }
    )
    assert res.current_estimate == 200000
    assert res.forecast[0].years_ahead == 3


def test_forecast_handles_json_with_markdown_fences():
    raw = (
        "```json\n"
        + json.dumps(
            {
                "current_estimate": 300000,
                "forecast": [
                    {"years_ahead": 1, "estimated_value": 309000,
                     "lower_bound": 290000, "upper_bound": 328000},
                ],
                "confidence": 0.6,
                "drivers": ["x"],
                "explanation": "ok",
            }
        )
        + "\n```"
    )
    parsed = PriceForecastTool._parse_llm_json(raw)
    assert parsed["current_estimate"] == 300000


def test_forecast_handles_llm_garbage_output():
    tool = _tool_with_llm({})  # empty payload
    res = tool.forecast(
        {
            "property_features": {"price": 150000},
            "horizon_years": [1],
        }
    )
    # Empty parsed -> fallback path kicks in
    assert res.current_estimate == 150000


def test_tool_metadata_and_run_format():
    tool = PriceForecastTool()
    assert tool.name == "price_forecast"
    out = tool._run(property_features={"price": 100000}, horizon_years=[1])
    # returns JSON-serializable string
    parsed = json.loads(out)
    assert "current_estimate" in parsed
    assert "forecast" in parsed