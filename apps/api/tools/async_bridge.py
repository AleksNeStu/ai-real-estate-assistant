"""Running a coroutine from code that may or may not have a loop.

The assistant reaches its tools from a worker thread as well as from the event
loop, and a tool that opens a database session has to do it on the loop that
will use the connection. This is the one place that knows the difference.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Coroutine, TypeVar

# What the coroutine answers is what the caller gets: the bridge does not
# reshape the result, so the type travels with it.
T = TypeVar("T")


def run_detached(coroutine: "Coroutine[Any, Any, T]") -> T:
    """Run a coroutine to the end, whatever loop the caller is in.

    Without a running loop the coroutine gets one of its own. With one, it
    runs on a worker thread — a session opened on the caller's loop cannot be
    used from this thread anyway.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coroutine)
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coroutine).result()
