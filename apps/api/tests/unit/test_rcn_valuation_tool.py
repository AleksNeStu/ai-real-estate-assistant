"""Tests for the tool that values a flat from the official register."""

from contextlib import asynccontextmanager
from datetime import date

from agents.services.valuation import RcnValuationProvider, ValuationOutcome
from tools.property_tools import create_property_tools
from tools.rcn_valuation_tool import RcnValuationTool, _format, _value


def _outcome() -> ValuationOutcome:
    return ValuationOutcome(
        estimated_value=710732.05,
        low=640000.0,
        high=780000.0,
        price_per_sqm_median=14214.64,
        sample_size=15,
        comparison_area="Topolowa, Kraków",
        period_start=date(2025, 10, 1),
        period_end=date(2026, 8, 27),
        confidence="medium",
        notes=["Only 3 sale(s) on Topolowa — the comparison fell back to the whole city."],
        comparables=[
            {
                "address": "TOPOLOWA, 48, KRAKÓW",
                "area_sqm": 38.72,
                "price": 790000.0,
                "price_per_sqm": 20402.89,
                "transaction_date": "2026-08-27",
                "rooms": 2,
                "floor": 3,
                "deed_reference": "Rep. A 18806/2026",
            }
        ],
        source="rcn",
    )


class TestFormat:
    def test_it_says_the_price_and_the_evidence(self):
        text = _format(_outcome())

        assert "710,732 PLN" in text
        assert "14,215 PLN/m²" in text
        assert "15 registered sale(s)" in text
        assert "2025-10-01" in text and "2026-08-27" in text
        assert "Confidence: medium" in text
        assert "TOPOLOWA, 48, KRAKÓW" in text
        assert "Rep. A 18806/2026" in text

    def test_it_says_so_when_there_is_no_answer(self):
        text = _format(ValuationOutcome(notes=["No sales of flats are registered in Gdańsk."]))

        assert "No estimate" in text
        assert "Gdańsk" in text


class TestRcnValuationTool:
    async def test_it_values_an_address(self, monkeypatch):
        async def _fake(city, street, area_sqm, rooms):
            assert city == "Kraków"
            assert street == "Topolowa"
            assert area_sqm == 50
            return _outcome()

        monkeypatch.setattr("tools.rcn_valuation_tool._value", _fake)
        tool = RcnValuationTool()

        text = await tool._arun(city="Kraków", street="Topolowa", area_sqm=50)

        assert "710,732 PLN" in text

    def test_it_values_an_address_from_sync_code(self, monkeypatch):
        async def _fake(city, street, area_sqm, rooms):
            return _outcome()

        monkeypatch.setattr("tools.rcn_valuation_tool._value", _fake)
        tool = RcnValuationTool()

        text = tool._run(city="Kraków", street="Topolowa", area_sqm=50)

        assert "710,732 PLN" in text

    async def test_a_register_that_cannot_be_read_is_reported(self, monkeypatch):
        async def _fake(city, street, area_sqm, rooms):
            raise RuntimeError("the register is unreachable")

        monkeypatch.setattr("tools.rcn_valuation_tool._value", _fake)
        tool = RcnValuationTool()

        text = await tool._arun(city="Kraków", area_sqm=50)

        assert "could not be read" in text


class TestTheValuePath:
    """The address on its way to the register."""

    async def test_it_reads_the_stored_register_in_a_session_of_its_own(self, monkeypatch):
        seen: dict = {}

        @asynccontextmanager
        async def _session():
            yield object()

        async def _provider_outcome(self, property_data):
            seen.update(property_data)
            return _outcome()

        monkeypatch.setattr("db.database.standalone_session", _session)
        monkeypatch.setattr(RcnValuationProvider, "outcome", _provider_outcome)

        outcome = await _value("Kraków", "Topolowa", 50, 2)

        assert outcome.estimated_value == 710732.05
        assert seen == {"city": "Kraków", "street": "Topolowa", "area_sqm": 50, "rooms": 2}


class TestToolbelt:
    def test_the_tool_is_offered_to_the_assistant(self):
        tools = create_property_tools()

        names = [tool.name for tool in tools]

        assert "rcn_property_valuation" in names

    def test_it_says_what_it_is_for(self):
        tool = RcnValuationTool()

        assert "register" in tool.description.lower()
        assert "worth" in tool.description.lower()
