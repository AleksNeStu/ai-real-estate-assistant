"""
Unit tests for WebScraperStubConnector.

Tests the stub connector for deterministic testing without network calls.

Task #72: MCP Web Scraper Connector
"""

import pytest

from mcp.config import MCPEdition
from mcp.stubs.web_scraper_stub import WebScraperStubConnector


class TestWebScraperStubConnectorAttributes:
    """Tests for stub connector class attributes."""

    def test_stub_name(self):
        """Test stub has correct name."""
        assert WebScraperStubConnector.name == "web_scraper_stub"

    def test_stub_display_name(self):
        """Test stub has correct display name."""
        assert "Stub" in WebScraperStubConnector.display_name

    def test_stub_allowlisted(self):
        """Test stub is allowlisted."""
        assert WebScraperStubConnector.allowlisted is True

    def test_stub_min_edition(self):
        """Test stub minimum edition is COMMUNITY."""
        assert WebScraperStubConnector.min_edition == MCPEdition.COMMUNITY

    def test_stub_no_api_key_required(self):
        """Test stub does not require API key."""
        assert WebScraperStubConnector.requires_api_key is False


class TestWebScraperStubConnectorAsync:
    """Async tests for WebScraperStubConnector."""

    @pytest.fixture
    def stub(self):
        """Create a stub instance for testing."""
        return WebScraperStubConnector()

    @pytest.mark.asyncio
    async def test_scrape_returns_default_response(self, stub):
        """Test scrape returns default response."""
        result = await stub.execute(
            "scrape",
            {
                "url": "https://example.com/test",
            },
        )

        assert result.success is True
        assert result.data["url"] == "https://example.com/test"
        assert "content" in result.data

    @pytest.mark.asyncio
    async def test_scrape_with_custom_selectors(self, stub):
        """Test scrape with custom selectors returns appropriate data."""
        result = await stub.execute(
            "scrape",
            {
                "url": "https://example.com/test",
                "selectors": {"title": "h1", "price": ".price"},
            },
        )

        assert result.success is True
        assert result.data["title"] == "Sample Page Title"
        assert result.data["price"] == "$1,234,567"

    @pytest.mark.asyncio
    async def test_scrape_batch_returns_results(self, stub):
        """Test scrape_batch returns results for all URLs."""
        result = await stub.execute(
            "scrape_batch",
            {
                "urls": [
                    "https://example.com/page1",
                    "https://example.com/page2",
                ],
            },
        )

        assert result.success is True
        assert result.data["total"] == 2
        assert result.data["successful"] == 2
        assert result.data["failed"] == 0

    @pytest.mark.asyncio
    async def test_validate_selector_valid(self, stub):
        """Test validate_selector with valid selector."""
        result = await stub.execute(
            "validate_selector",
            {
                "selector": "h1.title",
            },
        )

        assert result.success is True
        assert result.data["valid"] is True

    @pytest.mark.asyncio
    async def test_validate_selector_invalid(self, stub):
        """Test validate_selector with invalid selector."""
        result = await stub.execute(
            "validate_selector",
            {
                "selector": "h1[",  # Invalid selector
            },
        )

        assert result.success is True
        assert result.data["valid"] is False

    @pytest.mark.asyncio
    async def test_list_targets(self, stub):
        """Test list_targets returns allowed domains."""
        result = await stub.execute("list_targets")

        assert result.success is True
        assert "allowed_domains" in result.data

    @pytest.mark.asyncio
    async def test_unknown_operation(self, stub):
        """Test unknown operation returns error."""
        result = await stub.execute("unknown", {})

        assert result.success is False
        assert "Unknown operation" in str(result.errors)

    @pytest.mark.asyncio
    async def test_queued_response(self, stub):
        """Test queued response is returned."""
        stub.add_response({"title": "Custom Title", "content": "Custom content"})

        result = await stub.execute("scrape", {"url": "https://example.com/test"})

        assert result.success is True
        assert result.data["title"] == "Custom Title"

    @pytest.mark.asyncio
    async def test_queued_error(self, stub):
        """Test queued error is returned."""
        stub.add_error("Custom error message")

        result = await stub.execute("scrape", {"url": "https://example.com/test"})

        assert result.success is False
        assert "Custom error message" in result.errors

    @pytest.mark.asyncio
    async def test_blocked_response_helper(self, stub):
        """Test queue_blocked_response helper method."""
        stub.queue_blocked_response("https://example.com/blocked")

        result = await stub.execute("scrape", {"url": "https://example.com/blocked"})

        assert result.success is False
        assert "403" in str(result.errors)

    @pytest.mark.asyncio
    async def test_not_found_response_helper(self, stub):
        """Test queue_not_found_response helper method."""
        stub.queue_not_found_response("https://example.com/notfound")

        result = await stub.execute("scrape", {"url": "https://example.com/notfound"})

        assert result.success is False
        assert "404" in str(result.errors)

    @pytest.mark.asyncio
    async def test_timeout_response_helper(self, stub):
        """Test queue_timeout_response helper method."""
        stub.queue_timeout_response("https://example.com/timeout")

        result = await stub.execute("scrape", {"url": "https://example.com/timeout"})

        assert result.success is False
        assert "timed out" in str(result.errors).lower()

    @pytest.mark.asyncio
    async def test_call_history_recording(self, stub):
        """Test call history is recorded."""
        await stub.execute("scrape", {"url": "https://example.com/1"})
        await stub.execute("scrape", {"url": "https://example.com/2"})

        history = stub.get_call_history()

        assert len(history) == 2
        assert history[0].params["url"] == "https://example.com/1"
        assert history[1].params["url"] == "https://example.com/2"

    @pytest.mark.asyncio
    async def test_clear_history(self, stub):
        """Test clearing call history."""
        await stub.execute("scrape", {"url": "https://example.com/test"})
        stub.clear_history()

        assert len(stub.get_call_history()) == 0

    @pytest.mark.asyncio
    async def test_fail_rate(self, stub):
        """Test fail_rate causes random failures."""
        stub.set_fail_rate(1.0)  # 100% failure rate

        result = await stub.execute("scrape", {"url": "https://example.com/test"})

        assert result.success is False
        assert "Random failure" in str(result.errors)

    @pytest.mark.asyncio
    async def test_latency_simulation(self, stub, monkeypatch):
        """Test latency simulation adds delay."""
        import asyncio
        import time

        stub.set_latency(100)  # 100ms latency

        # The delay the stub asked for is the deterministic half of the
        # assertion; the wall-clock half only proves that the wait happened.
        requested: list[float] = []
        real_sleep = asyncio.sleep

        async def _record(delay: float, *args, **kwargs):
            requested.append(delay)
            return await real_sleep(delay, *args, **kwargs)

        monkeypatch.setattr(asyncio, "sleep", _record)

        start = time.perf_counter()
        await stub.execute("scrape", {"url": "https://example.com/test"})
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert requested == [0.1]
        # The floor is the latency minus the coarsest step of the platform
        # clock (15.6 ms), so the assertion survives a loaded machine.
        assert elapsed_ms >= 80

    @pytest.mark.asyncio
    async def test_reset_clears_state(self, stub):
        """Test reset clears all state."""
        stub.add_response({"test": "data"})
        stub.add_error("test error")
        await stub.execute("scrape", {"url": "https://example.com/test"})

        stub.reset()

        assert stub.call_count == 0
        assert len(stub.get_call_history()) == 0

    @pytest.mark.asyncio
    async def test_set_allowed_domains(self, stub):
        """Test set_allowed_domains updates list_targets response."""
        stub.set_allowed_domains(["custom.com", "*.custom.com"])

        result = await stub.execute("list_targets")

        assert result.data["allowed_domains"] == ["custom.com", "*.custom.com"]


class TestWebScraperStubNetworkIsolation:
    """Tests to verify stub never makes network calls."""

    @pytest.mark.asyncio
    async def test_no_network_calls(self):
        """Verify stub never makes network calls using NetworkGuard."""
        from mcp.testing.network_guard import NetworkGuard

        stub = WebScraperStubConnector()

        with NetworkGuard.enabled():
            # This should NOT raise NetworkGuardError
            result = await stub.execute(
                "scrape",
                {
                    "url": "https://example.com/test",
                },
            )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_stub_is_network_isolated(self):
        """Test is_network_isolated property is True."""
        stub = WebScraperStubConnector()
        assert stub.is_network_isolated is True
