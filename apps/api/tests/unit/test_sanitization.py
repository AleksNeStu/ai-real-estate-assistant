"""
Tests for input sanitization utilities.

Regression coverage for issue #377: the control-character filter used to be a
``bytes`` table passed to ``str.translate()``. ``str.translate()`` looks a
bytes table up by ordinal, so the 62-byte table rewrote every code point below
0x3E - spaces, digits and punctuation included - and mangled non-Latin text.
"""

from typing import Any

import pytest

from utils.sanitization import (
    ALLOWED_CONTROL,
    CONTROL_CHARS,
    CONTROL_CHARS_FILTER,
    sanitize_chat_message,
    sanitize_email,
    sanitize_for_logging,
    sanitize_property_id,
    sanitize_search_query,
    sanitize_string,
)


class TestControlCharacterFiltering:
    """Control characters must be removed without touching printable text."""

    def test_ascii_digits_spaces_and_punctuation_survive(self):
        """Regression: spaces, digits and punctuation were replaced by garbage bytes."""
        text = "2 bedroom apartment under 500000 EUR"
        assert sanitize_string(text) == text

    def test_cjk_text_with_digits_survives(self):
        """Regression for issue #377: CJK input lost its adjacent ASCII digits."""
        assert sanitize_string("预算是50万人民币") == "预算是50万人民币"
        assert sanitize_string("编号A7391号") == "编号A7391号"

    def test_cyrillic_and_accented_text_survive(self):
        assert sanitize_string("Квартира за 2 500 000 EUR") == "Квартира за 2 500 000 EUR"
        assert sanitize_string("Appartement à 250 000 €") == "Appartement à 250 000 €"

    def test_control_characters_are_removed(self):
        for cp in (0x00, 0x01, 0x08, 0x0B, 0x0C, 0x1F, 0x7F, 0x80, 0x9F):
            assert chr(cp) not in sanitize_string(f"a{chr(cp)}b")

    def test_allowed_whitespace_is_not_treated_as_a_control_character(self):
        """Tab/LF/CR are allowed by the filter; sanitize_string normalizes whitespace later."""
        for cp in ALLOWED_CONTROL:
            assert cp not in CONTROL_CHARS_FILTER
        assert ALLOWED_CONTROL == {0x09, 0x0A, 0x0D}
        # Whitespace collapsing is the documented behaviour of sanitize_string.
        assert sanitize_string("a\tb\nc\rd") == "a b c d"

    def test_filter_is_a_code_point_mapping_not_a_bytes_table(self):
        """Guard against reintroducing the bytes table that caused issue #377."""
        assert isinstance(CONTROL_CHARS_FILTER, dict)
        assert all(value is None for value in CONTROL_CHARS_FILTER.values())
        assert all(isinstance(key, int) for key in CONTROL_CHARS_FILTER)

    def test_output_contains_no_control_characters(self):
        """Nothing outside the allowed whitespace may survive sanitization."""
        result = sanitize_string("price 42 000 €\x00\x7f\nend")
        assert not [c for c in result if ord(c) < 0x20 and c not in "\t\n\r"]
        assert not [c for c in result if 0x7F <= ord(c) <= 0x9F]

    def test_filter_covers_every_declared_control_character(self):
        for cp in CONTROL_CHARS:
            if cp in ALLOWED_CONTROL:
                continue
            assert chr(cp) not in sanitize_string(f"x{chr(cp)}y")


class TestSanitizeString:
    def test_non_string_returns_empty_string(self):
        non_str: Any = None
        assert sanitize_string(non_str) == ""
        non_str = 123
        assert sanitize_string(non_str) == ""

    def test_length_limit_raises(self):
        with pytest.raises(ValueError, match="maximum length"):
            sanitize_string("x" * 20, max_length=10)

    def test_html_is_stripped(self):
        assert sanitize_string("<b>hello</b>") == "hello"
        assert sanitize_string("<script>alert(1)</script>ok") == "ok"

    def test_html_stripping_keeps_digits(self):
        assert sanitize_string("<span>2 rooms</span>") == "2 rooms"

    def test_excessive_whitespace_is_collapsed(self):
        assert sanitize_string("a    b") == "a b"

    def test_allow_control_chars_keeps_everything(self):
        assert sanitize_string("a\x00b", allow_control_chars=True) == "a\x00b"


class TestSanitizeSearchQuery:
    def test_query_with_numbers_and_spaces_is_unchanged(self):
        query = "2 bedroom apartment under 500000 EUR in Warsaw"
        assert sanitize_search_query(query) == query

    def test_empty_query_raises(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            sanitize_search_query("")

    def test_control_characters_removed(self):
        assert sanitize_search_query("warsaw\x00") == "warsaw"


class TestSanitizeChatMessage:
    def test_message_with_numbers_is_unchanged(self):
        message = "Show me 3 rooms under 500k"
        assert sanitize_chat_message(message) == message

    def test_cjk_message_with_numbers_is_unchanged(self):
        message = "预算是50万人民币"
        assert sanitize_chat_message(message) == message

    def test_blank_message_raises(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            sanitize_chat_message("   ")


class TestSanitizeEmail:
    def test_email_is_lowercased(self):
        assert sanitize_email("User@Example.COM") == "user@example.com"

    def test_invalid_email_raises(self):
        with pytest.raises(ValueError, match="Invalid email"):
            sanitize_email("not-an-email")

    def test_email_with_digits_is_preserved(self):
        assert sanitize_email("user123@example.com") == "user123@example.com"


class TestSanitizePropertyId:
    def test_path_traversal_is_removed(self):
        assert sanitize_property_id("../../etc/passwd") == "etcpasswd"

    def test_id_with_digits_is_preserved(self):
        assert sanitize_property_id("prop-42-a") == "prop-42-a"

    def test_empty_id_raises(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            sanitize_property_id("")


class TestSanitizeForLogging:
    def test_newlines_are_flattened(self):
        assert sanitize_for_logging("line1\nline2\rline3") == "line1 line2 line3"

    def test_digits_are_preserved(self):
        assert sanitize_for_logging("session 12345 took 42 ms") == "session 12345 took 42 ms"

    def test_control_characters_are_removed(self):
        assert sanitize_for_logging("a\x00b\x7fc") == "abc"

    def test_long_values_are_truncated(self):
        result = sanitize_for_logging("x" * 100, max_length=50)
        assert len(result) == 50
        assert result.endswith("...")
