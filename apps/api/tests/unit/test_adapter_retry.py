"""
Tests for adapter retry logic with exponential backoff.

This module tests the retry decorator and error handling in adapters.
"""

from unittest.mock import MagicMock

import pytest
import requests

from data.adapters.base import RETRYABLE_EXCEPTIONS, with_retry


class TestRetryDecorator:
    """Tests for the with_retry decorator."""

    def test_retry_on_connection_error(self):
        """Verify retry on connection failure."""
        call_count = 0

        @with_retry(max_tries=3, max_time=5)
        def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Simulated connection error")
            return "success"

        result = failing_function()
        assert result == "success"
        assert call_count == 3

    def test_retry_on_timeout(self):
        """Verify retry on timeout."""
        call_count = 0

        @with_retry(max_tries=3, max_time=5)
        def timing_out():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise TimeoutError("Request timed out")
            return "success"

        result = timing_out()
        assert result == "success"
        assert call_count == 2

    def test_retry_exhausted_raises_exception(self):
        """Verify final exception after max retries exhausted."""
        call_count = 0

        @with_retry(max_tries=2, max_time=3)
        def always_failing():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Persistent failure")

        with pytest.raises(ConnectionError, match="Persistent failure"):
            always_failing()

        assert call_count == 2

    def test_no_retry_on_success(self):
        """Verify no retry when function succeeds."""
        call_count = 0

        @with_retry(max_tries=3, max_time=5)
        def successful_function():
            nonlocal call_count
            call_count += 1
            return "success"

        result = successful_function()
        assert result == "success"
        assert call_count == 1

    def test_retry_on_os_error(self):
        """Verify retry on OSError (includes socket errors)."""
        call_count = 0

        @with_retry(max_tries=3, max_time=5)
        def socket_error():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise OSError("Socket error")
            return "success"

        result = socket_error()
        assert result == "success"
        assert call_count == 2

    def test_no_retry_on_non_retryable_exception(self):
        """Verify no retry for non-retryable exceptions."""
        call_count = 0

        @with_retry(max_tries=3, max_time=5)
        def value_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("Not retryable")

        with pytest.raises(ValueError, match="Not retryable"):
            value_error()

        assert call_count == 1

    def test_retry_callback_called(self):
        """Verify retry callback is invoked."""
        retry_events = []

        def on_retry(attempt, wait_time, exception):
            retry_events.append(
                {
                    "attempt": attempt,
                    "wait_time": wait_time,
                    "exception": exception,
                }
            )

        call_count = 0

        @with_retry(max_tries=3, max_time=5, on_retry=on_retry)
        def failing_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary failure")
            return "success"

        result = failing_then_success()
        assert result == "success"
        assert len(retry_events) == 2  # Two retries before success


class TestRetryableExceptions:
    """Tests for retryable exception types."""

    def test_connection_error_is_retryable(self):
        """ConnectionError should be in retryable exceptions."""
        assert ConnectionError in RETRYABLE_EXCEPTIONS

    def test_timeout_error_is_retryable(self):
        """TimeoutError should be in retryable exceptions."""
        assert TimeoutError in RETRYABLE_EXCEPTIONS

    def test_os_error_is_retryable(self):
        """OSError should be in retryable exceptions."""
        assert OSError in RETRYABLE_EXCEPTIONS


class TestRetryWithRequests:
    """Tests for retry with requests library exceptions."""

    def test_retry_on_requests_connection_error(self):
        """Verify retry on requests.ConnectionError."""
        call_count = 0

        @with_retry(max_tries=3, max_time=5)
        def request_failing():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise requests.ConnectionError("Network error")
            return MagicMock(status_code=200)

        result = request_failing()
        assert result.status_code == 200
        assert call_count == 2

    def test_retry_on_requests_timeout(self):
        """Verify retry on requests.Timeout."""
        call_count = 0

        @with_retry(max_tries=3, max_time=5)
        def timeout_request():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise requests.Timeout("Request timeout")
            return MagicMock(status_code=200)

        result = timeout_request()
        assert result.status_code == 200
        assert call_count == 2
