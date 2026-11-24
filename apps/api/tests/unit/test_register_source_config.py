"""A source of the kind "register" is checked when it is written.

The register is read from the database, so a source of that kind names a
city the site knows and a window it reads. A source that cannot read
anything is refused when it is written - not when it is synced, in the
middle of a run nobody is watching.
"""

import pytest

from api.routers.data_sources import _validate_config


def test_a_register_source_of_a_known_city_passes() -> None:
    """A city the site knows, and nothing else, is enough."""
    _validate_config("register", {"city": "Kraków"})


def test_a_register_source_of_an_unknown_city_is_refused() -> None:
    """The register source names a city the site knows."""
    with pytest.raises(ValueError, match="unknown city"):
        _validate_config("register", {"city": "Atlantis"})


def test_a_register_source_without_a_city_is_refused() -> None:
    """Without a city there is nothing to read."""
    with pytest.raises(ValueError, match="requires 'city'"):
        _validate_config("register", {})


def test_a_register_source_with_a_window_passes() -> None:
    """The window is optional, and it is read as the config names it."""
    _validate_config("register", {"city": "Kraków", "since": "2026-01-01", "limit": 100})


def test_a_register_source_with_a_bad_date_is_refused() -> None:
    """A date the reader cannot parse is refused with the value named."""
    with pytest.raises(ValueError, match="not a date"):
        _validate_config("register", {"city": "Kraków", "since": "yesterday"})


def test_a_register_source_with_a_bad_limit_is_refused() -> None:
    """A limit that is not a number is refused with the value named."""
    with pytest.raises(ValueError, match="not a number"):
        _validate_config("register", {"city": "Kraków", "limit": "many"})


def test_a_register_source_with_a_limit_of_zero_is_refused() -> None:
    """A limit of zero sales is a source that reads nothing."""
    with pytest.raises(ValueError, match="positive"):
        _validate_config("register", {"city": "Kraków", "limit": 0})


def test_a_register_source_with_a_limit_above_the_bound_is_refused() -> None:
    """A limit that asks for every sale of a busy city is refused by name.

    The read is bounded: the deployment holds the listings of the sales it
    read in memory while the sync runs. A source that asks for more than the
    bound is told so when it is written - where the answer can still be
    given - and not silently read as a smaller one.
    """
    with pytest.raises(ValueError, match="must not be more than"):
        _validate_config("register", {"city": "Kraków", "limit": 10_000_000})


def test_a_limit_written_as_a_decimal_does_not_slip_past_the_bound() -> None:
    """The limit is read the same way the bound is checked.

    A limit of 10000000.0 is the same number as a limit of 10000000, and
    one written as 1e7 is the same number again. A reading of the limit
    that took the text of a number literally would let all three past a
    bound that is there to hold the memory of the deployment.
    """
    for limit in (10_000_000.0, "10000000.0", 1e7, "1e7"):
        with pytest.raises(ValueError, match="must not be more than"):
            _validate_config("register", {"city": "Kraków", "limit": limit})


def test_a_register_source_with_a_limit_that_is_not_a_whole_number_is_refused() -> None:
    """Half a sale is not a sale, and a limit is not quietly rounded."""
    with pytest.raises(ValueError, match="whole number"):
        _validate_config("register", {"city": "Kraków", "limit": 1.5})


def test_a_limit_that_is_not_a_finite_number_is_refused() -> None:
    """An endless limit is not a number of sales."""
    for limit in ("inf", "-inf", "nan", float("inf"), float("nan")):
        with pytest.raises(ValueError, match="not a number"):
            _validate_config("register", {"city": "Kraków", "limit": limit})
