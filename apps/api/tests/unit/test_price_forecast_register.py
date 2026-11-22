"""The forecast when the official register holds the place.

Before the register was wired in, a forecast that could not be produced by the
model fell back to a flat 3% a year. That was a constant wearing a forecast's
clothes. These tests hold the line: with the register, the projection follows
the rate the registered prices actually moved at, and without it the constant
survives only as a labelled assumption.
"""

import json
from datetime import date
from typing import Optional

from agents.services.valuation import RegisterContext
from services.rcn_valuation import MarketTrend
from tools.price_forecast_tools import PriceForecastTool

TREND = MarketTrend(
    annual_rate=0.08,
    sample_size=312,
    period_start=date(2024, 1, 15),
    period_end=date(2026, 8, 27),
    median_early=13000.0,
    median_late=15200.0,
    comparison_area="Kraków",
)

REGISTER = RegisterContext(
    median_price_per_sqm=14316.0,
    trend=TREND,
    sample_size=312,
    comparison_area="Kraków",
    period_start=date(2024, 1, 15),
    period_end=date(2026, 8, 27),
)


def _reader(context):
    def read(city: str, street: str = ""):
        return context if city else None

    return read


def _tool(context: Optional[RegisterContext] = REGISTER) -> PriceForecastTool:
    # No model: the deterministic fallback is the path under test.
    tool = PriceForecastTool(vector_store=None, llm=None, register_reader=_reader(context))
    tool._llm = None
    return tool


class TestTheForecastFallsBackToTheRegister:
    def test_anchors_the_estimate_on_the_registered_median(self):
        tool = _tool()

        result = tool.forecast({"property_features": {"city": "Kraków", "area_sqm": 50}})

        # 14 316 PLN/m² over 50 m².
        assert result.current_estimate == 715800
        assert result.median_price_per_sqm == 14316.0

    def test_projects_with_the_rate_the_prices_moved_at(self):
        tool = _tool()

        result = tool.forecast({"property_features": {"city": "Kraków", "area_sqm": 50}})

        # 8% a year, not the flat 3%.
        one_year = result.forecast[0].estimated_value
        assert 715800 * 1.07 < one_year < 715800 * 1.09

    def test_says_the_rate_was_measured_and_where_it_came_from(self):
        tool = _tool()

        result = tool.forecast({"property_features": {"city": "Kraków", "area_sqm": 50}})

        assert "8.0%" in result.explanation
        assert "312" in result.explanation
        assert any("312" in driver for driver in result.drivers)

    def test_counts_the_registered_sales_as_the_comparables(self):
        tool = _tool()

        result = tool.forecast({"property_features": {"city": "Kraków", "area_sqm": 50}})

        assert result.comparables_used == 312
        assert result.confidence > 0.4


class _FakeModel:
    """A model that answers with a fixed JSON, and remembers the prompt."""

    def __init__(self, answer: str):
        self.answer = answer
        self.prompts: list[str] = []

    def invoke(self, prompt):
        self.prompts.append(prompt)
        return type("_Answer", (), {"content": self.answer})()


class TestTheModelAnswers:
    """The model answered, so the register goes into the prompt."""

    def _tool(self, model, context: Optional[RegisterContext] = REGISTER) -> PriceForecastTool:
        return PriceForecastTool(vector_store=None, llm=model, register_reader=_reader(context))

    def test_the_register_reaches_the_prompt(self):
        model = _FakeModel(
            json.dumps(
                {
                    "current_estimate": 715800,
                    "forecast": [{"years_ahead": 1, "estimated_value": 773000}],
                    "confidence": 0.7,
                    "drivers": ["the register"],
                    "explanation": "from the register",
                }
            )
        )
        tool = self._tool(model)

        tool.forecast({"property_features": {"city": "Kraków", "area_sqm": 50}})

        prompt = model.prompts[0]
        assert "Official register median price-per-sqm (Kraków): 14316" in prompt
        assert "312 registered sales" in prompt
        assert "Registered price change: +8.0% a year" in prompt

    def test_a_model_that_returns_no_curve_is_projected_with_the_measured_rate(self):
        model = _FakeModel(
            json.dumps({"current_estimate": 715800, "forecast": [], "confidence": 0.6})
        )
        tool = self._tool(model)

        result = tool.forecast({"property_features": {"city": "Kraków", "area_sqm": 50}})

        # The model gave no curve, so the measured rate projects it: 8%, not
        # the flat 3%.
        one_year = result.forecast[0].estimated_value
        assert 715800 * 1.07 < one_year < 715800 * 1.09

    def test_a_model_without_a_rate_falls_back_to_the_labelled_assumption(self):
        model = _FakeModel(
            json.dumps({"current_estimate": 715800, "forecast": [], "confidence": 0.6})
        )
        context = RegisterContext(
            median_price_per_sqm=14316.0,
            trend=None,
            sample_size=40,
            comparison_area="Kraków",
        )
        tool = self._tool(model, context=context)

        result = tool.forecast({"property_features": {"city": "Kraków", "area_sqm": 50}})

        one_year = result.forecast[0].estimated_value
        assert 715800 * 1.02 < one_year < 715800 * 1.04

    def test_a_property_without_a_city_reads_no_register(self):
        tool = PriceForecastTool(vector_store=None, llm=None, register_reader=_reader(REGISTER))

        result = tool.forecast({"property_features": {"area_sqm": 50}})

        assert result.current_estimate == 0.0


class TestTheForecastWithoutTheRegister:
    def test_keeps_the_flat_assumption_and_says_it_is_one(self):
        tool = _tool(context=None)

        result = tool.forecast({"property_features": {"city": "Madrid", "area_sqm": 100}})

        assert "flat 3%" in result.explanation
        assert result.confidence <= 0.35

    def test_does_not_read_the_register_when_there_is_none_to_read(self):
        tool = PriceForecastTool(vector_store=None, llm=None)

        result = tool.forecast({"property_features": {"city": "Kraków", "area_sqm": 50}})

        assert result.current_estimate == 0.0

    def test_a_register_without_a_measured_rate_says_the_rate_is_an_assumption(self):
        context = RegisterContext(
            median_price_per_sqm=14316.0,
            trend=None,
            sample_size=40,
            comparison_area="Kraków",
        )
        tool = _tool(context=context)

        result = tool.forecast({"property_features": {"city": "Kraków", "area_sqm": 50}})

        assert result.current_estimate == 715800
        assert "assumption" in result.explanation
        assert "could not be measured" in " ".join(result.drivers)
