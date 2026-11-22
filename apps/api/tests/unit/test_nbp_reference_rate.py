"""The mortgage rate comes from NBP, not from a constant (Task #112).

The tools that price a mortgage and the total cost of ownership read the NBP
reference rate at request time. These tests pin three things: how the bank's
file is read, the payment that follows from the rate in it, and the fact that
an answer names the rate it used and the date that rate was published.

The last test asks NBP itself and is skipped when the network is not there.
"""

import math
import urllib.request
from unittest.mock import MagicMock, patch

import pytest

from services.fx_rates import (
    NBP_REFERENCE_RATE_FALLBACK,
    NBP_REFERENCE_RATE_URL,
    NbpReferenceRate,
    _fetch_nbp_reference_rate,
    _parse_nbp_reference_rate,
    get_nbp_reference_rate,
)
from tools.mortgage_tools import MortgageCalculatorTool
from tools.tco_tools import TCOCalculatorTool

# The response NBP returned on 2026-11-22, recorded verbatim.
NBP_BASE_RATES_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<stopy_procentowe data_publikacji="2026-03-05">
    <tabela
        id="stoproc"
        naglowek="Stopa procentowa:"
        header="NBP base rates:">
        <pozycja
            id="ref"
            nazwa="Stopa referencyjna"
            name="Reference rate (minimum money market intervention rate)"
            odnosnik="1"
            oprocentowanie="3,75"
            trend = "spadek"
            obowiazuje_od="2026-03-05" />
        <pozycja
            id="lom"
            nazwa="Stopa lombardowa"
            name="Lombard rate"
            oprocentowanie="4,25"
            trend = "spadek"
            obowiazuje_od="2026-03-05" />
        <pozycja
            id="dep"
            nazwa="Stopa depozytowa"
            name="NBP deposit rate"
            oprocentowanie="3,25"
            trend = "spadek"
            obowiazuje_od="2026-03-05" />
    </tabela>
</stopy_procentowe>
"""

# The values the recorded response carries.
RECORDED_RATE = 3.75
RECORDED_PUBLISHED_AT = "2026-03-05"


def _mock_urlopen(content: bytes):
    """Create a mock urlopen context manager returning content."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = content
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


def _monthly_payment(principal: float, annual_rate: float, years: int = 30) -> float:
    """The amortisation formula, written out so the test does not trust the code."""
    monthly_rate = (annual_rate / 100) / 12
    payments = years * 12
    factor = math.pow(1 + monthly_rate, payments)
    return principal * monthly_rate * factor / (factor - 1)


class TestReadingTheNbpFile:
    """How the bank's base-rates file is turned into a rate."""

    def test_the_recorded_response_yields_the_reference_rate(self):
        rate = _parse_nbp_reference_rate(NBP_BASE_RATES_XML)

        assert rate is not None
        assert rate.rate == RECORDED_RATE
        assert rate.published_at == RECORDED_PUBLISHED_AT
        assert rate.effective_from == RECORDED_PUBLISHED_AT
        assert rate.is_fallback is False

    def test_the_decimal_comma_is_read_as_a_decimal_point(self):
        """NBP writes 3,75 - the rate is 3.75 percent, not 375."""
        rate = _parse_nbp_reference_rate(NBP_BASE_RATES_XML)

        assert rate is not None
        assert rate.rate == pytest.approx(3.75)

    def test_a_file_without_the_reference_rate_yields_nothing(self):
        rate = _parse_nbp_reference_rate('<stopy_procentowe data_publikacji="2026-03-05" />')

        assert rate is None

    @patch("services.fx_rates.urllib.request.urlopen")
    def test_the_fetch_reads_the_file(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen(NBP_BASE_RATES_XML.encode())

        rate = _fetch_nbp_reference_rate()

        assert rate is not None
        assert rate.rate == RECORDED_RATE

    @patch("services.fx_rates.urllib.request.urlopen", side_effect=Exception("network error"))
    def test_the_fetch_degrades_when_the_network_is_down(self, mock_urlopen):
        assert _fetch_nbp_reference_rate() is None


class TestTheRateTheToolsUse:
    """What the tools compute with, and what they answer."""

    def _recorded_rate(self) -> NbpReferenceRate:
        return NbpReferenceRate(
            rate=RECORDED_RATE,
            published_at=RECORDED_PUBLISHED_AT,
            effective_from=RECORDED_PUBLISHED_AT,
        )

    @patch("tools.mortgage_tools.get_nbp_reference_rate")
    def test_the_mortgage_payment_uses_the_nbp_rate(self, mock_rate):
        mock_rate.return_value = self._recorded_rate()

        result = MortgageCalculatorTool.calculate(property_price=300000)

        assert result.interest_rate == RECORDED_RATE
        assert result.monthly_payment == pytest.approx(
            _monthly_payment(300000 * 0.8, RECORDED_RATE)
        )

    @patch("tools.mortgage_tools.get_nbp_reference_rate")
    def test_the_tco_payment_uses_the_nbp_rate(self, mock_rate):
        mock_rate.return_value = self._recorded_rate()

        result = TCOCalculatorTool.calculate(property_price=300000)

        assert result.interest_rate == RECORDED_RATE
        assert result.monthly_mortgage == pytest.approx(
            _monthly_payment(300000 * 0.8, RECORDED_RATE)
        )
        # The TCO is the mortgage plus the running costs (maintenance is 1%).
        assert result.monthly_tco > result.monthly_mortgage

    @patch("tools.mortgage_tools.get_nbp_reference_rate")
    def test_a_caller_supplied_rate_is_used_as_it_is(self, mock_rate):
        """A rate the caller gives is the caller's rate - NBP is not consulted."""
        mock_rate.return_value = self._recorded_rate()

        result = MortgageCalculatorTool.calculate(property_price=300000, interest_rate=5.0)

        assert result.interest_rate == 5.0
        assert result.monthly_payment == pytest.approx(_monthly_payment(300000 * 0.8, 5.0))
        assert "caller-specified" in result.interest_rate_source

    @patch("tools.mortgage_tools.get_nbp_reference_rate")
    def test_the_answer_names_the_rate_and_its_date(self, mock_rate):
        mock_rate.return_value = self._recorded_rate()

        answer = MortgageCalculatorTool()._run(property_price=300000)

        assert "3.75%" in answer
        assert RECORDED_PUBLISHED_AT in answer

    @patch("tools.mortgage_tools.get_nbp_reference_rate")
    def test_the_tco_answer_names_the_rate_and_its_date(self, mock_rate):
        mock_rate.return_value = self._recorded_rate()

        answer = TCOCalculatorTool()._run(property_price=300000)

        assert "3.75%" in answer
        assert RECORDED_PUBLISHED_AT in answer


class TestTheOfflineFallback:
    """What happens when the network is not there."""

    @patch("services.fx_rates.urllib.request.urlopen", side_effect=Exception("network error"))
    def test_the_fallback_is_labelled(self, mock_urlopen, tmp_path, monkeypatch):
        monkeypatch.setattr("services.fx_rates.CACHE_DIR", tmp_path)

        rate = get_nbp_reference_rate()

        assert rate.is_fallback is True
        assert rate.rate == NBP_REFERENCE_RATE_FALLBACK
        assert rate.published_at is not None
        assert "fallback" in rate.label

    @patch("services.fx_rates.urllib.request.urlopen", side_effect=Exception("network error"))
    def test_the_tool_says_when_it_fell_back(self, mock_urlopen, tmp_path, monkeypatch):
        monkeypatch.setattr("services.fx_rates.CACHE_DIR", tmp_path)

        result = MortgageCalculatorTool.calculate(property_price=300000)

        assert result.interest_rate == NBP_REFERENCE_RATE_FALLBACK
        assert "fallback" in result.interest_rate_source


class TestTheLiveRate:
    """What NBP publishes right now."""

    def test_the_live_file_carries_a_reference_rate(self):
        request = urllib.request.Request(
            NBP_REFERENCE_RATE_URL, headers={"User-Agent": "fx-rates/1.0"}
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as resp:  # nosec B310
                content = resp.read().decode("utf-8-sig")
        except Exception as e:  # noqa: BLE001 - the network is out of our hands
            pytest.skip(f"the network is not available: {e}")

        rate = _parse_nbp_reference_rate(content)

        assert rate is not None
        assert rate.rate > 0
        assert rate.published_at is not None
