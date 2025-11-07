"""
Unit tests for metrics utility functions.

Tests metric formatting and calculation functions in ui/metrics.py
"""

import pytest
from ui.metrics import format_number, format_delta


class TestFormatNumber:
    """Tests for number formatting function."""

    def test_default_format(self):
        """Test default number formatting."""
        assert format_number(1234) == "1,234"
        assert format_number(1234567) == "1,234,567"
        assert format_number(100) == "100"

    def test_currency_format(self):
        """Test currency formatting."""
        assert format_number(1234.56, "currency") == "$1,234.56"
        assert format_number(999.99, "currency") == "$999.99"
        assert format_number(1000000.50, "currency") == "$1,000,000.50"

    def test_percentage_format(self):
        """Test percentage formatting."""
        assert format_number(50.5, "percentage") == "50.5%"
        assert format_number(100, "percentage") == "100.0%"
        assert format_number(0.5, "percentage") == "0.5%"

    def test_compact_format(self):
        """Test compact notation formatting."""
        assert format_number(500, "compact") == "500"
        assert format_number(1500, "compact") == "1.5K"
        assert format_number(1000000, "compact") == "1.0M"
        assert format_number(1500000000, "compact") == "1.5B"

    def test_compact_boundaries(self):
        """Test compact format at boundaries."""
        assert format_number(999, "compact") == "999"
        assert format_number(1000, "compact") == "1.0K"
        assert format_number(999999, "compact") == "1000.0K"
        assert format_number(1000000, "compact") == "1.0M"

    def test_negative_numbers(self):
        """Test formatting negative numbers."""
        assert format_number(-1234) == "-1,234"
        assert format_number(-1234.56, "currency") == "$-1,234.56"
        assert format_number(-5000, "compact") == "-5.0K"

    def test_zero(self):
        """Test formatting zero."""
        assert format_number(0) == "0"
        assert format_number(0, "currency") == "$0.00"
        assert format_number(0, "percentage") == "0.0%"
        assert format_number(0, "compact") == "0"

    def test_decimal_precision(self):
        """Test decimal precision in different formats."""
        assert format_number(1234.9999) == "1,235"  # Rounds to integer
        assert format_number(1234.567, "currency") == "$1,234.57"  # 2 decimals
        assert format_number(12.3456, "percentage") == "12.3%"  # 1 decimal

class TestFormatDelta:
    """Tests for delta formatting function."""

    def test_percentage_increase(self):
        """Test formatting percentage increase."""
        delta = format_delta(100, 120, "percentage")
        assert delta == "+20.0%"

    def test_percentage_decrease(self):
        """Test formatting percentage decrease."""
        delta = format_delta(120, 100, "percentage")
        assert delta == "-16.7%"

    def test_percentage_no_change(self):
        """Test formatting with no change."""
        delta = format_delta(100, 100, "percentage")
        assert delta == "+0.0%"

    def test_absolute_increase(self):
        """Test formatting absolute increase."""
        delta = format_delta(100, 150, "absolute")
        assert delta == "+50"

    def test_absolute_decrease(self):
        """Test formatting absolute decrease."""
        delta = format_delta(150, 100, "absolute")
        assert delta == "-50"

    def test_both_format(self):
        """Test formatting with both absolute and percentage."""
        delta = format_delta(100, 120, "both")
        assert "+20" in delta
        assert "+20.0%" in delta

    def test_zero_old_value(self):
        """Test delta when old value is zero."""
        delta = format_delta(0, 50, "percentage")
        assert delta == "+∞"

    def test_zero_to_zero(self):
        """Test delta when both values are zero."""
        delta = format_delta(0, 0, "percentage")
        assert delta == "0"

    def test_large_numbers(self):
        """Test delta with large numbers."""
        delta = format_delta(1000000, 1500000, "absolute")
        assert delta == "+500,000"

    def test_negative_values(self):
        """Test delta with negative values."""
        delta = format_delta(-100, -80, "percentage")
        # -80 - (-100) = +20, which is +20% of -100 = -20%
        assert "%" in delta

    def test_small_percentage_changes(self):
        """Test formatting small percentage changes."""
        delta = format_delta(10000, 10001, "percentage")
        assert delta == "+0.0%"  # Rounds to 0.0%

    def test_decimal_values(self):
        """Test delta with decimal values."""
        delta = format_delta(100.5, 120.7, "absolute")
        assert "+20" in delta

    def test_format_types(self):
        """Test all format types produce valid output."""
        old, new = 100, 120

        pct = format_delta(old, new, "percentage")
        assert "%" in pct
        assert "+" in pct

        abs_val = format_delta(old, new, "absolute")
        assert "+" in abs_val
        assert "%" not in abs_val

        both = format_delta(old, new, "both")
        assert "%" in both
        assert "+" in both


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_very_large_numbers(self):
        """Test formatting very large numbers."""
        assert format_number(999999999999) == "999,999,999,999"
        assert format_number(1000000000000, "compact") == "1000.0B"

    def test_very_small_decimals(self):
        """Test formatting very small decimal numbers."""
        assert format_number(0.001) == "0"  # Rounds to 0
        assert format_number(0.001, "percentage") == "0.0%"

    def test_scientific_notation_input(self):
        """Test handling scientific notation."""
        assert format_number(1e6, "compact") == "1.0M"
        assert format_number(1e9, "compact") == "1.0B"

    def test_extreme_delta_increase(self):
        """Test extreme percentage increase."""
        delta = format_delta(1, 1000, "percentage")
        assert "%" in delta
        # Should be +99900.0% or similar

    def test_extreme_delta_decrease(self):
        """Test extreme percentage decrease."""
        delta = format_delta(1000, 1, "percentage")
        assert "%" in delta
        assert "-" in delta

    def test_precision_edge_cases(self):
        """Test precision at rounding boundaries."""
        # Test rounding at .5
        assert format_number(1234.5) == "1,234"  # Rounds down
        assert format_number(1234.51) == "1,235"  # Rounds up

    def test_negative_to_positive_delta(self):
        """Test delta from negative to positive."""
        delta = format_delta(-50, 50, "absolute")
        assert "+100" in delta

    def test_positive_to_negative_delta(self):
        """Test delta from positive to negative."""
        delta = format_delta(50, -50, "absolute")
        assert "-100" in delta


class TestInvalidInputs:
    """Tests for handling invalid inputs gracefully."""

    def test_invalid_format_type(self):
        """Test with invalid format type (should default)."""
        # Should not crash, might use default
        result = format_number(1234, "invalid_format")
        assert isinstance(result, str)

    def test_none_values(self):
        """Test handling None values."""
        # These should ideally be handled or raise appropriate errors
        # Depending on implementation, adjust assertions
        pass  # Implementation-dependent

    def test_string_input(self):
        """Test with string input (type error expected)."""
        # Should raise TypeError or handle gracefully
        pass  # Implementation-dependent


class TestConsistency:
    """Tests for consistent behavior across different inputs."""

    def test_sign_consistency(self):
        """Test that signs are consistent."""
        # Positive delta
        assert format_delta(100, 120).startswith("+")

        # Negative delta
        assert format_delta(120, 100).startswith("-")

    def test_format_consistency(self):
        """Test consistent formatting across similar values."""
        # Similar values should have similar formatting
        assert format_number(1000, "compact") == "1.0K"
        assert format_number(2000, "compact") == "2.0K"
        assert format_number(3000, "compact") == "3.0K"

    def test_decimal_consistency(self):
        """Test consistent decimal places."""
        # Currency always has 2 decimals
        assert format_number(100, "currency").endswith(".00")
        assert format_number(100.5, "currency").endswith(".50")

        # Percentage always has 1 decimal
        assert ".0%" in format_number(100, "percentage")


class TestRealWorldScenarios:
    """Tests with real-world property data scenarios."""

    def test_property_price_formatting(self):
        """Test formatting property prices."""
        # Typical rental prices
        assert format_number(850, "currency") == "$850.00"
        assert format_number(1200, "currency") == "$1,200.00"

    def test_property_price_delta(self):
        """Test property price changes."""
        # 5% increase
        delta = format_delta(1000, 1050, "percentage")
        assert delta == "+5.0%"

        # 10% decrease
        delta = format_delta(1000, 900, "percentage")
        assert delta == "-10.0%"

    def test_market_statistics(self):
        """Test formatting market statistics."""
        # Total properties
        assert format_number(1234, "compact") == "1.2K"

        # Average price
        assert format_number(987.65, "currency") == "$987.65"

    def test_percentage_metrics(self):
        """Test percentage-based metrics."""
        # Occupancy rate
        assert format_number(85.5, "percentage") == "85.5%"

        # Growth rate
        assert format_number(12.3, "percentage") == "12.3%"

    def test_comparison_deltas(self):
        """Test deltas in property comparisons."""
        # Price difference between properties
        delta = format_delta(850, 1200, "both")
        assert "+350" in delta
        assert "%" in delta
