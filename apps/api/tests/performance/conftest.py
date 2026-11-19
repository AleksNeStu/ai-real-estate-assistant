"""Performance test configuration and fixtures."""

import asyncio
import os
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

import pytest
import pytest_asyncio
from httpx import AsyncClient

# The backend the suites measure. It is a variable, not a constant: the
# suites are run against a local server, against the compose stack, or
# against a deployment - and a percentile is only a measurement of the
# machine that produced it, so the URL has to be named by whoever runs them.
PERF_BASE_URL = os.environ.get("PERF_BASE_URL", "http://localhost:8000").rstrip("/")


def pytest_configure(config: pytest.Config) -> None:
    """Register the markers this directory uses."""
    config.addinivalue_line(
        "markers",
        "performance: a measurement of the response times (not a unit test)",
    )
    config.addinivalue_line(
        "markers",
        "benchmark: a p95 measurement against a running backend",
    )
    config.addinivalue_line(
        "markers",
        "load: a load measurement - resource intensive, opt in with RUN_LOAD_TESTS=1",
    )
    config.addinivalue_line(
        "markers",
        "database: a measurement of the database layer",
    )


@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""

    response_times: list[float] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)
    status_codes: dict[int, int] = field(default_factory=lambda: defaultdict(int))

    def add_response(self, response_time: float, status_code: int) -> None:
        """Add a response measurement."""
        self.response_times.append(response_time)
        self.status_codes[status_code] += 1

    def add_error(self, error: dict[str, Any]) -> None:
        """Add an error record."""
        self.errors.append(error)

    @property
    def total_requests(self) -> int:
        """Total number of requests made."""
        return len(self.response_times)

    @property
    def success_rate(self) -> float:
        """Calculate success rate (2xx and 3xx responses)."""
        if not self.response_times:
            return 0.0
        successful = sum(count for code, count in self.status_codes.items() if 200 <= code < 400)
        return successful / len(self.response_times) * 100

    def percentile(self, p: float) -> float:
        """Calculate the p-th percentile of response times."""
        if not self.response_times:
            return 0.0
        sorted_times = sorted(self.response_times)
        index = int(len(sorted_times) * p / 100)
        return sorted_times[min(index, len(sorted_times) - 1)]

    @property
    def p50(self) -> float:
        """Median response time."""
        return self.percentile(50)

    @property
    def p95(self) -> float:
        """95th percentile response time."""
        return self.percentile(95)

    @property
    def p99(self) -> float:
        """99th percentile response time."""
        return self.percentile(99)

    @property
    def avg(self) -> float:
        """Average response time."""
        if not self.response_times:
            return 0.0
        return sum(self.response_times) / len(self.response_times)

    @property
    def min(self) -> float:
        """Minimum response time."""
        return min(self.response_times) if self.response_times else 0.0

    @property
    def max(self) -> float:
        """Maximum response time."""
        return max(self.response_times) if self.response_times else 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "total_requests": self.total_requests,
            "success_rate": f"{self.success_rate:.2f}%",
            "response_times": {
                "min": f"{self.min:.3f}s",
                "avg": f"{self.avg:.3f}s",
                "p50": f"{self.p50:.3f}s",
                "p95": f"{self.p95:.3f}s",
                "p99": f"{self.p99:.3f}s",
                "max": f"{self.max:.3f}s",
            },
            "status_codes": dict(self.status_codes),
            "errors": self.errors,
        }


@pytest.fixture
def metrics() -> PerformanceMetrics:
    """Create a fresh metrics container."""
    return PerformanceMetrics()


@pytest.fixture
def performance_thresholds() -> dict[str, dict[str, float]]:
    """Performance thresholds for different endpoints."""
    return {
        "search": {
            "p95_max": 2.0,  # 2 seconds
            "avg_max": 1.0,  # 1 second
            "success_rate_min": 99.0,  # 99%
        },
        "chat": {
            "p95_max": 8.0,  # 8 seconds (LLM processing)
            "avg_max": 5.0,  # 5 seconds
            "success_rate_min": 95.0,  # 95%
        },
        "documents": {
            "p95_max": 5.0,  # 5 seconds for 10MB
            "avg_max": 2.0,  # 2 seconds
            "success_rate_min": 99.0,  # 99%
        },
        "health": {
            "p95_max": 0.1,  # 100ms
            "avg_max": 0.05,  # 50ms
            "success_rate_min": 100.0,  # 100%
        },
        "leads": {
            "p95_max": 1.0,  # 1 second
            "avg_max": 0.5,  # 500ms
            "success_rate_min": 99.0,  # 99%
        },
    }


def _reject_rate_limited(response) -> None:
    """A 429 is not a measurement.

    The limiter answered, not the product - and a percentile computed over
    limiter responses is a percentile of the limiter. The suite says so
    instead of reporting a number that means nothing.
    """
    if response.status_code == 429:
        raise AssertionError(
            "the backend rate-limited the measurement (429). Raise its rate limit "
            "(API_RATE_LIMIT_RPM) above the suite's request count - otherwise the "
            "suite measures the limiter, not the product."
        )


@pytest_asyncio.fixture
async def perf_client():
    """
    Create an async HTTP client for performance testing.

    The suite measures a backend, so the backend has to be there. Without
    one the measurement is skipped with the reason - not a wall of
    connection errors, and not a number that means nothing.
    """
    if not _backend_reachable():
        pytest.skip(
            f"no backend at {PERF_BASE_URL} - start one and point PERF_BASE_URL at it. "
            "A percentile is a measurement of the machine that produced it."
        )
    async with AsyncClient(
        base_url=PERF_BASE_URL,
        timeout=30.0,
        follow_redirects=True,
        event_hooks={"response": [_reject_rate_limited]},
    ) as client:
        yield client


@pytest_asyncio.fixture
async def authed_perf_client(perf_client: AsyncClient, api_key: str):
    """Create an authenticated async HTTP client for performance testing."""
    perf_client.headers["X-API-Key"] = api_key
    yield perf_client


_BACKEND_REACHABLE: bool | None = None


def _backend_reachable() -> bool:
    """Whether a backend answers at PERF_BASE_URL. Asked once per run."""
    global _BACKEND_REACHABLE
    if _BACKEND_REACHABLE is None:
        import urllib.error
        import urllib.request

        try:
            with urllib.request.urlopen(f"{PERF_BASE_URL}/health", timeout=5) as response:
                _BACKEND_REACHABLE = response.status < 500
        except urllib.error.HTTPError as error:
            # A degraded backend still answers - it is measurable.
            _BACKEND_REACHABLE = error.code < 500
        except Exception:
            _BACKEND_REACHABLE = False
    return bool(_BACKEND_REACHABLE)


@pytest.fixture
def api_key() -> str:
    """Get API key for testing."""
    return os.environ.get("API_ACCESS_KEY", "test-api-key")


async def measure_request(
    client: AsyncClient,
    method: str,
    url: str,
    metrics: PerformanceMetrics,
    **kwargs: Any,
) -> tuple[float, int]:
    """Measure a single HTTP request and record metrics."""
    start_time = time.perf_counter()
    try:
        response = await getattr(client, method.lower())(url, **kwargs)
        elapsed = time.perf_counter() - start_time
        metrics.add_response(elapsed, response.status_code)
        return elapsed, response.status_code
    except Exception as e:
        elapsed = time.perf_counter() - start_time
        metrics.add_error(
            {
                "url": url,
                "method": method,
                "error": str(e),
                "elapsed": elapsed,
            }
        )
        metrics.add_response(elapsed, 0)
        raise


async def concurrent_requests(
    client: AsyncClient,
    method: str,
    url: str,
    num_requests: int,
    metrics: PerformanceMetrics,
    **kwargs: Any,
) -> list[tuple[float, int]]:
    """Execute concurrent requests and collect metrics."""
    tasks = [measure_request(client, method, url, metrics, **kwargs) for _ in range(num_requests)]
    return await asyncio.gather(*tasks, return_exceptions=True)  # type: ignore[return-value]


@pytest.fixture
def benchmark_results() -> dict[str, Any]:
    """Container for benchmark results."""
    return {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "results": {},
        "passed": True,
        "failures": [],
    }
