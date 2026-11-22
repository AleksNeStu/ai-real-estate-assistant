"""Tests for the forecast endpoint, read directly.

The tool behind the endpoint is tested on its own; what is under test here is
the wiring: the request is validated, the features are resolved and the tool
is built with the register reader, so an answer is anchored on the official
prices whenever the register holds the place.
"""

import pytest
from fastapi import HTTPException

from api.models import PriceForecastRequest
from api.routers.valuation import price_forecast


def _no_model(monkeypatch):
    """The endpoint is tested without a model: the deterministic path."""
    monkeypatch.setattr("tools.price_forecast_tools.resolve_tool_llm", lambda *args, **kwargs: None)


class TestTheForecastEndpoint:
    async def test_it_forecasts_the_features_it_was_given(self, monkeypatch):
        _no_model(monkeypatch)
        monkeypatch.setattr(
            "api.routers.valuation.read_register_context_sync",
            lambda city, street="": None,
        )
        request = PriceForecastRequest(property_features={"city": "Kraków", "area_sqm": 50})

        result = await price_forecast(request, None, None)  # type: ignore[arg-type]

        assert result.horizon_years == [1, 3, 5]
        assert [point.years_ahead for point in result.forecast] == [1, 3, 5]
        assert result.explanation

    async def test_it_reads_the_register_through_the_injected_reader(self, monkeypatch):
        """The reader is the endpoint's own; the register answers through it."""
        seen: list[tuple] = []

        def _reader(city, street=""):
            seen.append((city, street))
            return None

        _no_model(monkeypatch)
        monkeypatch.setattr("api.routers.valuation.read_register_context_sync", _reader)
        request = PriceForecastRequest(
            property_features={"city": "Kraków", "street": "Topolowa", "area_sqm": 50}
        )

        await price_forecast(request, None, None)  # type: ignore[arg-type]

        assert seen == [("Kraków", "Topolowa")]

    async def test_a_request_without_a_property_is_refused(self, monkeypatch):
        _no_model(monkeypatch)
        request = PriceForecastRequest()

        with pytest.raises(HTTPException) as refused:
            await price_forecast(request, None, None)  # type: ignore[arg-type]

        assert refused.value.status_code == 400

    async def test_a_property_that_is_not_in_the_catalogue_is_refused(self, monkeypatch):
        _no_model(monkeypatch)
        request = PriceForecastRequest(property_id="prop-404")

        with pytest.raises(HTTPException) as refused:
            await price_forecast(request, None, None)  # type: ignore[arg-type]

        assert refused.value.status_code == 404
