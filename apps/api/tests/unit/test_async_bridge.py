"""Tests for the bridge that runs a coroutine from any thread.

The assistant reaches its tools from a worker thread as well as from the event
loop, and a tool that opens a database session has to do it on the loop that
will use the connection. The bridge is the one place that knows the
difference, so it is the one place that is tested here.
"""

import asyncio

from tools.async_bridge import run_detached


class TestTheBridge:
    def test_it_runs_a_coroutine_without_a_loop(self):
        async def _work():
            return 42

        assert run_detached(_work()) == 42

    async def test_it_runs_a_coroutine_from_inside_a_running_loop(self):
        async def _work():
            await asyncio.sleep(0)
            return 42

        # The caller already owns a loop, so the coroutine runs on a worker
        # thread with a loop of its own — a connection opened on the caller's
        # loop cannot be used from this one anyway.
        assert run_detached(_work()) == 42

    async def test_the_result_is_the_caller_s(self):
        async def _work():
            return {"value": 7}

        result = run_detached(_work())

        assert result == {"value": 7}

    async def test_a_failing_coroutine_raises(self):
        async def _work():
            raise RuntimeError("the register is unreachable")

        try:
            run_detached(_work())
        except RuntimeError as exc:
            assert "unreachable" in str(exc)
        else:  # pragma: no cover - the coroutine always raises
            raise AssertionError("the failure did not reach the caller")
