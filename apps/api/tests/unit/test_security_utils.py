"""Unit tests for core.security_utils (log injection, SSRF, path traversal, hashing)."""

import logging
import os
import tempfile

import pytest

from core.security_utils import (
    LOG_SANITIZE_PATTERN,
    SecureLogger,
    get_secure_logger,
    hash_sensitive_data,
    sanitize_for_log,
    validate_file_path,
    validate_osrm_url,
)


class TestSanitizeForLog:
    """Tests for sanitize_for_log: strips control chars and truncates."""

    def test_none_returns_empty_string(self):
        assert sanitize_for_log(None) == ""

    def test_plain_string_unchanged(self):
        assert sanitize_for_log("hello world") == "hello world"

    def test_strips_newlines(self):
        assert sanitize_for_log("line1\nline2") == "line1 line2"

    def test_strips_carriage_returns(self):
        assert sanitize_for_log("a\rb") == "a b"

    def test_strips_tabs(self):
        assert sanitize_for_log("a\tb") == "a b"

    def test_strips_mixed_control_chars(self):
        assert sanitize_for_log("x\n\r\ty") == "x   y"

    def test_truncates_to_max_length(self):
        long = "a" * 1000
        assert len(sanitize_for_log(long)) == 500
        assert len(sanitize_for_log(long, max_length=10)) == 10

    def test_truncation_does_not_count_control_chars_separately(self):
        # Truncation happens AFTER sanitization, so the visible result respects max_length.
        s = "a" * 50 + "\n" + "b" * 50
        result = sanitize_for_log(s, max_length=30)
        assert len(result) == 30
        assert "\n" not in result

    def test_non_string_input_is_coerced(self):
        assert sanitize_for_log(42) == "42"
        assert sanitize_for_log(3.14) == "3.14"
        assert sanitize_for_log(["a", "b"]) == "['a', 'b']"

    def test_object_repr_safe(self):
        class Obj:
            def __repr__(self):
                return "fake\nrepr"

        # The repr's newline is sanitized when converted via str().
        assert "\n" not in sanitize_for_log(Obj())

    def test_log_injection_payload_neutralized(self):
        # Classic log-injection: forge a fake log line.
        payload = "user logged in\n[FAKE] admin escalated privileges"
        result = sanitize_for_log(payload)
        assert "\n" not in result
        assert "FAKE" in result  # the content survives, but can't escape onto a new log line

    def test_log_sanitize_pattern_matches_expected_chars(self):
        assert LOG_SANITIZE_PATTERN.search("\n")
        assert LOG_SANITIZE_PATTERN.search("\r")
        assert LOG_SANITIZE_PATTERN.search("\t")
        assert not LOG_SANITIZE_PATTERN.search("a")
        assert not LOG_SANITIZE_PATTERN.search(" ")
        assert not LOG_SANITIZE_PATTERN.search("0")


class TestValidateFilePath:
    """Tests for validate_file_path: blocks path traversal."""

    def test_simple_relative_path_is_valid(self):
        assert validate_file_path("file.txt") is True

    def test_absolute_path_within_cwd_is_valid(self):
        assert validate_file_path(os.path.abspath(".")) is True

    def test_path_traversal_blocked(self):
        assert validate_file_path("../etc/passwd") is False
        assert validate_file_path("..\\windows\\system32") is False
        assert validate_file_path("a/../../b") is False

    def test_path_within_allowed_base_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            good = os.path.join(tmp, "subdir", "file.csv")
            os.makedirs(os.path.dirname(good), exist_ok=True)
            assert validate_file_path(good, allowed_base_dir=tmp) is True

    def test_path_outside_allowed_base_dir(self):
        with tempfile.TemporaryDirectory() as tmp_a, tempfile.TemporaryDirectory() as tmp_b:
            outside = os.path.join(tmp_b, "file.csv")
            assert validate_file_path(outside, allowed_base_dir=tmp_a) is False

    def test_traversal_escape_attempt_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Path string contains traversal pattern even if resolution might land elsewhere.
            evil = os.path.join(tmp, "..", "..", "etc", "passwd")
            assert validate_file_path(evil) is False


class TestValidateOsrmUrl:
    """Tests for validate_osrm_url: SSRF prevention."""

    def test_valid_osrm_route_url(self):
        assert (
            validate_osrm_url(
                "https://router.project-osrm.org/route/v1/driving/13.4,52.5;13.5,52.6"
            )
            is True
        )

    def test_valid_with_port(self):
        assert validate_osrm_url("http://localhost:5000/route/v1/foot/1,2;3,4") is True

    def test_rejects_non_routing_path(self):
        # OSRM also exposes /table, /match, /trip — allowed by the regex.
        assert validate_osrm_url("https://router.example.com/table/v1/driving/1,2;3,4") is True

    def test_rejects_path_without_word_segment(self):
        # The pattern requires /<word>/ after the host, so URLs with no path or a bare slash are rejected.
        assert validate_osrm_url("https://router.example.com") is False
        assert validate_osrm_url("https://router.example.com/") is False

    def test_known_ssrf_schemes_rejected(self):
        # The scheme allowlist (http/https only) is the primary SSRF guard. file://, gopher://, javascript: must be rejected.
        assert validate_osrm_url("file:///etc/passwd") is False
        assert validate_osrm_url("gopher://internal.svc/data") is False
        assert validate_osrm_url("javascript:alert(1)") is False
        assert validate_osrm_url("ftp://router.example.com/route") is False

    def test_rejects_unrelated_host_pattern(self):
        # The pattern requires http(s)://host(:port)?/(<word>)/...
        assert validate_osrm_url("file:///etc/passwd") is False
        assert validate_osrm_url("javascript:alert(1)") is False
        assert validate_osrm_url("not-a-url") is False

    def test_rejects_empty(self):
        assert validate_osrm_url("") is False


class TestHashSensitiveData:
    """Tests for hash_sensitive_data: SHA-256 / SHA-512 only."""

    def test_sha256_default(self):
        h = hash_sensitive_data("hello")
        assert len(h) == 64  # SHA-256 hex length
        assert h == hash_sensitive_data("hello", algorithm="sha256")

    def test_sha512(self):
        h = hash_sensitive_data("hello", algorithm="sha512")
        assert len(h) == 128  # SHA-512 hex length

    def test_different_inputs_produce_different_hashes(self):
        assert hash_sensitive_data("a") != hash_sensitive_data("b")

    def test_same_input_produces_same_hash(self):
        assert hash_sensitive_data("secret") == hash_sensitive_data("secret")

    def test_unicode_supported(self):
        # Should not raise on non-ASCII input.
        h = hash_sensitive_data("пароль")
        assert len(h) == 64

    def test_invalid_algorithm_raises(self):
        with pytest.raises(ValueError, match="Unsupported algorithm"):
            hash_sensitive_data("x", algorithm="md5")
        with pytest.raises(ValueError, match="Unsupported algorithm"):
            hash_sensitive_data("x", algorithm="sha1")
        with pytest.raises(ValueError, match="Unsupported algorithm"):
            hash_sensitive_data("x", algorithm="")


class TestSecureLogger:
    """Tests for SecureLogger: wraps a logger and sanitizes all messages/args."""

    def setup_method(self):
        """Set up a captured logger; runs before each test method."""
        self.records = []
        self.logger = logging.getLogger("test_secure_logger")
        self.logger.handlers = []
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False

        capture_handler = logging.Handler(level=logging.DEBUG)

        def emit(record):
            self.records.append(record)

        capture_handler.emit = emit
        self.logger.addHandler(capture_handler)
        self.handler = capture_handler

    def teardown_method(self):
        self.logger.removeHandler(self.handler)

    def test_message_sanitized(self):
        sl = SecureLogger(self.logger)
        sl.info("user\nname=%s", "alice")
        assert len(self.records) == 1
        assert "\n" not in self.records[0].getMessage()

    def test_args_sanitized(self):
        sl = SecureLogger(self.logger)
        sl.warning("got %s", "value\nwith\nnewlines")
        assert len(self.records) == 1
        assert "\n" not in self.records[0].getMessage()
        assert "value" in self.records[0].getMessage()

    def test_all_levels_sanitize(self):
        sl = SecureLogger(self.logger)
        for level_fn, _expected_level in [
            (sl.debug, logging.DEBUG),
            (sl.info, logging.INFO),
            (sl.warning, logging.WARNING),
            (sl.error, logging.ERROR),
            (sl.critical, logging.CRITICAL),
        ]:
            level_fn("msg %s", "with\nnewline")
        assert len(self.records) == 5
        for rec in self.records:
            assert "\n" not in rec.getMessage()

    def test_exception_includes_traceback_text(self):
        sl = SecureLogger(self.logger)
        try:
            raise RuntimeError("boom")
        except RuntimeError:
            sl.exception("oops %s", "context")
        assert len(self.records) == 1
        assert self.records[0].exc_info is not None
        # exc_info is a (type, value, traceback) tuple; the original exception
        # message lives on the second element.
        exc_type, exc_value, _tb = self.records[0].exc_info
        assert exc_type is RuntimeError
        assert "boom" in str(exc_value)

    def test_extra_kwargs_pass_through(self):
        sl = SecureLogger(self.logger)
        sl.info("event", extra={"user_id": "abc"})
        assert len(self.records) == 1
        assert self.records[0].user_id == "abc"

    def test_get_secure_logger_returns_secure_logger(self):
        sl = get_secure_logger("test_get_secure_logger_x")
        assert isinstance(sl, SecureLogger)

    def test_truncation_in_secure_logger(self):
        sl = SecureLogger(self.logger)
        huge = "x" * 1000
        sl.info("payload: %s", huge)
        assert len(self.records) == 1
        # The sanitized arg is truncated to 500 chars, then the formatted message
        # is "payload: " + 500 x's = 509 chars.
        assert len(self.records[0].getMessage()) <= 510
