"""Tests for MCPStub base class."""

import pytest

from mcp.config import MCPEdition
from mcp.stubs.base_stub import MCPStub, StubCallRecord


class ConcreteStub(MCPStub[dict]):
    """Concrete implementation for testing."""

    name = "test_stub"
    display_name = "Test Stub"
    description = "Test stub for unit testing"

    async def execute(self, operation, params=None, **kwargs):
        await self._simulate_latency()
        result = self._get_next_response(operation)
        self._record_call(operation, params, kwargs, result=result)
        return result


class TestStubCallRecord:
    """Tests for StubCallRecord dataclass."""

    def test_create_record(self) -> None:
        """Test creating a call record."""
        record = StubCallRecord(
            operation="search",
            params={"query": "test"},
            kwargs={"timeout": 30},
        )

        assert record.operation == "search"
        assert record.params == {"query": "test"}
        assert record.kwargs == {"timeout": 30}
        assert record.result is None
        assert record.error is None
        assert record.timestamp is not None


class TestMCPStubAttributes:
    """Tests for MCPStub class attributes."""

    def test_stub_attributes(self) -> None:
        """Test stub has correct default attributes."""
        assert ConcreteStub.name == "test_stub"
        assert ConcreteStub.display_name == "Test Stub"
        assert ConcreteStub.requires_api_key is False
        assert ConcreteStub.allowlisted is True
        assert ConcreteStub.min_edition == MCPEdition.COMMUNITY
        assert ConcreteStub.supports_streaming is True

    def test_stub_no_api_key_required(self) -> None:
        """Test stub doesn't require API key."""
        stub = ConcreteStub()
        assert stub is not None


class TestMCPStubResponseQueue:
    """Tests for response queue functionality."""

    def test_add_response(self) -> None:
        """Test adding a response to the queue."""
        stub = ConcreteStub()
        stub.add_response({"data": "test"})

        assert len(stub._response_queue) == 1

    def test_add_responses(self) -> None:
        """Test adding multiple responses."""
        stub = ConcreteStub()
        stub.add_responses([{"data": 1}, {"data": 2}, {"data": 3}])

        assert len(stub._response_queue) == 3

    def test_add_error(self) -> None:
        """Test adding an error to the queue."""
        stub = ConcreteStub()
        stub.add_error("Test error")

        assert len(stub._error_queue) == 1

    def test_initial_responses(self) -> None:
        """Test initializing with responses."""
        stub = ConcreteStub(responses=[{"data": 1}, {"data": 2}])

        assert len(stub._response_queue) == 2


class TestMCPStubCallHistory:
    """Tests for call history recording."""

    def test_record_call(self) -> None:
        """Test recording a call."""
        stub = ConcreteStub()
        stub._record_call("search", {"query": "test"}, {})

        history = stub.get_call_history()
        assert len(history) == 1
        assert history[0].operation == "search"

    def test_get_last_call(self) -> None:
        """Test getting the last call."""
        stub = ConcreteStub()
        stub._record_call("op1", {}, {})
        stub._record_call("op2", {}, {})

        last = stub.get_last_call()
        assert last is not None
        assert last.operation == "op2"

    def test_get_last_call_empty(self) -> None:
        """Test getting last call when empty."""
        stub = ConcreteStub()
        assert stub.get_last_call() is None

    def test_clear_history(self) -> None:
        """Test clearing call history."""
        stub = ConcreteStub()
        stub._record_call("test", {}, {})
        stub.clear_history()

        assert len(stub.get_call_history()) == 0

    def test_disable_recording(self) -> None:
        """Test disabling call recording."""
        stub = ConcreteStub(record_calls=False)
        stub._record_call("test", {}, {})

        assert len(stub.get_call_history()) == 0


class TestMCPStubAsync:
    """Async tests for MCPStub."""

    @pytest.mark.asyncio
    async def test_connect(self) -> None:
        """Test connect always succeeds."""
        stub = ConcreteStub()

        result = await stub.connect()

        assert result is True
        assert stub.is_connected() is True

    @pytest.mark.asyncio
    async def test_disconnect(self) -> None:
        """Test disconnect."""
        stub = ConcreteStub()
        await stub.connect()

        await stub.disconnect()

        assert stub.is_connected() is False

    @pytest.mark.asyncio
    async def test_health_check(self) -> None:
        """Test health check returns stub info."""
        stub = ConcreteStub()

        result = await stub.health_check()

        assert result.success is True
        assert result.data is not None
        assert result.data["healthy"] is True
        assert result.data["stub_type"] == "ConcreteStub"

    @pytest.mark.asyncio
    async def test_execute_with_queued_response(self) -> None:
        """Test execute returns queued response."""
        stub = ConcreteStub()
        stub.add_response({"data": "test_response"})

        result = await stub.execute("search", {"query": "test"})

        assert result.success is True
        assert result.data == {"data": "test_response"}

    @pytest.mark.asyncio
    async def test_execute_with_queued_error(self) -> None:
        """Test execute returns queued error."""
        stub = ConcreteStub()
        stub.add_error("Test error")

        result = await stub.execute("search", {})

        assert result.success is False
        assert "Test error" in result.errors

    @pytest.mark.asyncio
    async def test_simulated_latency(self, monkeypatch) -> None:
        """Test simulated latency.

        The stub ASKS for the latency with a sleep; the wall clock of the
        machine is not asked to honour it. The event loop of Windows reads
        its clock in 15.6 ms steps, so a 50 ms sleep can return a few
        milliseconds early - the stub is right, the clock is coarse. The
        assertion on the requested delay is the exact one; the floor on the
        measured time is the platform's, not the stub's.
        """
        import asyncio
        import time

        stub = ConcreteStub(latency_ms=50)

        requested: list[float] = []
        real_sleep = asyncio.sleep

        async def _record(delay: float, *args, **kwargs):
            requested.append(delay)
            return await real_sleep(delay, *args, **kwargs)

        monkeypatch.setattr(asyncio, "sleep", _record)

        start = time.perf_counter()
        await stub.execute("test", {})
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert requested == [0.05]
        # The floor is the latency minus the coarsest step of the platform
        # clock (15.6 ms), so the assertion survives a loaded machine.
        assert elapsed_ms >= 30

    @pytest.mark.asyncio
    async def test_stream(self) -> None:
        """Test default streaming implementation."""
        stub = ConcreteStub()
        stub.add_response({"data": "stream_test"})

        chunks = []
        async for chunk in stub.stream("search", {}):
            chunks.append(chunk)

        assert len(chunks) == 1
        assert chunks[0] == {"data": "stream_test"}


class TestMCPStubStateManagement:
    """Tests for stub state management."""

    def test_set_latency(self) -> None:
        """Test setting latency."""
        stub = ConcreteStub()
        stub.set_latency(100)

        assert stub._latency_ms == 100

    def test_set_fail_rate(self) -> None:
        """Test setting fail rate."""
        stub = ConcreteStub()
        stub.set_fail_rate(0.5)

        assert stub._fail_rate == 0.5

    def test_set_fail_rate_invalid(self) -> None:
        """Test setting invalid fail rate."""
        stub = ConcreteStub()

        with pytest.raises(ValueError):
            stub.set_fail_rate(1.5)

    def test_reset(self) -> None:
        """Test reset clears all state."""
        stub = ConcreteStub(latency_ms=100, fail_rate=0.5)
        stub.add_response({"data": "test"})
        stub._record_call("test", {}, {})

        stub.reset()

        assert stub._call_count == 0
        assert len(stub._response_queue) == 0
        assert len(stub._call_history) == 0
        assert stub._latency_ms == 0.0
        assert stub._fail_rate == 0.0

    def test_call_count(self) -> None:
        """Test call count property."""
        stub = ConcreteStub()
        assert stub.call_count == 0

    def test_is_network_isolated(self) -> None:
        """Test stub is always network isolated."""
        stub = ConcreteStub()
        assert stub.is_network_isolated is True
