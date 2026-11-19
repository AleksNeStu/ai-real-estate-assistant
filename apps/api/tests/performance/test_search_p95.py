"""Search endpoint p95 performance benchmark tests (Task #50).

Measures p95 latency for various search query patterns:
- Simple text searches
- Filtered searches (price, location, rooms)
- Complex queries with sorting and pagination

SLA Target: p95 < 2s for search endpoints.
"""

import statistics
from typing import Any

import pytest
from httpx import AsyncClient

# Test configuration
WARMUP_REQUESTS = 5
BENCHMARK_REQUESTS = 50  # Number of requests for p95 calculation
P95_TARGET_MS = 2000.0  # 2 seconds
P99_TARGET_MS = 5000.0  # 5 seconds (allowable spike)
AVG_TARGET_MS = 1000.0  # 1 second average


class BenchmarkStats:
    """Calculate benchmark statistics from raw measurements."""

    def __init__(self, measurements: list[float]) -> None:
        self.measurements = sorted(measurements)
        self.count = len(measurements)

    @property
    def min_ms(self) -> float:
        return self.measurements[0] * 1000 if self.measurements else 0.0

    @property
    def max_ms(self) -> float:
        return self.measurements[-1] * 1000 if self.measurements else 0.0

    @property
    def avg_ms(self) -> float:
        return statistics.mean(self.measurements) * 1000 if self.measurements else 0.0

    @property
    def median_ms(self) -> float:
        return statistics.median(self.measurements) * 1000 if self.measurements else 0.0

    @property
    def p95_ms(self) -> float:
        if not self.measurements:
            return 0.0
        index = int(self.count * 0.95)
        return self.measurements[min(index, self.count - 1)] * 1000

    @property
    def p99_ms(self) -> float:
        if not self.measurements:
            return 0.0
        index = int(self.count * 0.99)
        return self.measurements[min(index, self.count - 1)] * 1000

    @property
    def std_dev_ms(self) -> float:
        if len(self.measurements) < 2:
            return 0.0
        return statistics.stdev(self.measurements) * 1000

    def to_dict(self) -> dict[str, Any]:
        return {
            "count": self.count,
            "min_ms": round(self.min_ms, 2),
            "max_ms": round(self.max_ms, 2),
            "avg_ms": round(self.avg_ms, 2),
            "median_ms": round(self.median_ms, 2),
            "p95_ms": round(self.p95_ms, 2),
            "p99_ms": round(self.p99_ms, 2),
            "std_dev_ms": round(self.std_dev_ms, 2),
        }


@pytest.mark.benchmark
@pytest.mark.asyncio
class TestSimpleSearchBenchmark:
    """Benchmark tests for simple text search queries."""

    async def test_simple_text_search_p95(
        self,
        authed_perf_client: AsyncClient,
    ) -> None:
        """Simple text search should have p95 < 2s."""
        measurements: list[float] = []
        query = {"query": "apartments in Berlin", "limit": 10}

        # Warmup
        for _ in range(WARMUP_REQUESTS):
            await authed_perf_client.post("/api/v1/search", json=query)

        # Benchmark
        for _ in range(BENCHMARK_REQUESTS):
            import time

            start = time.perf_counter()
            response = await authed_perf_client.post("/api/v1/search", json=query)
            elapsed = time.perf_counter() - start
            measurements.append(elapsed)
            assert response.status_code == 200

        stats = BenchmarkStats(measurements)

        # Assertions
        assert stats.p95_ms < P95_TARGET_MS, (
            f"Simple search p95 ({stats.p95_ms:.0f}ms) exceeds target ({P95_TARGET_MS:.0f}ms)\n"
            f"Stats: {stats.to_dict()}"
        )
        assert stats.avg_ms < AVG_TARGET_MS, (
            f"Simple search avg ({stats.avg_ms:.0f}ms) exceeds target ({AVG_TARGET_MS:.0f}ms)"
        )
        assert stats.p99_ms < P99_TARGET_MS, (
            f"Simple search p99 ({stats.p99_ms:.0f}ms) exceeds target ({P99_TARGET_MS:.0f}ms)"
        )

    async def test_simple_search_short_query_p95(
        self,
        authed_perf_client: AsyncClient,
    ) -> None:
        """Short text queries should be faster."""
        measurements: list[float] = []
        query = {"query": "Berlin", "limit": 10}

        # Warmup
        for _ in range(WARMUP_REQUESTS):
            await authed_perf_client.post("/api/v1/search", json=query)

        # Benchmark
        for _ in range(BENCHMARK_REQUESTS):
            import time

            start = time.perf_counter()
            response = await authed_perf_client.post("/api/v1/search", json=query)
            elapsed = time.perf_counter() - start
            measurements.append(elapsed)
            assert response.status_code == 200

        stats = BenchmarkStats(measurements)

        # Short queries should be faster than average
        assert stats.p95_ms < P95_TARGET_MS, (
            f"Short query p95 ({stats.p95_ms:.0f}ms) exceeds target ({P95_TARGET_MS:.0f}ms)"
        )
        assert stats.avg_ms < AVG_TARGET_MS * 0.8, (
            f"Short query avg ({stats.avg_ms:.0f}ms) should be < 80% of target"
        )


@pytest.mark.benchmark
@pytest.mark.asyncio
class TestFilteredSearchBenchmark:
    """Benchmark tests for filtered search queries."""

    async def test_price_filter_search_p95(
        self,
        authed_perf_client: AsyncClient,
    ) -> None:
        """Price-filtered search should have p95 < 2s."""
        measurements: list[float] = []
        query = {
            "query": "apartments",
            "filters": {
                "price_min": 100000,
                "price_max": 500000,
            },
            "limit": 10,
        }

        # Warmup
        for _ in range(WARMUP_REQUESTS):
            await authed_perf_client.post("/api/v1/search", json=query)

        # Benchmark
        for _ in range(BENCHMARK_REQUESTS):
            import time

            start = time.perf_counter()
            response = await authed_perf_client.post("/api/v1/search", json=query)
            elapsed = time.perf_counter() - start
            measurements.append(elapsed)
            assert response.status_code == 200

        stats = BenchmarkStats(measurements)

        assert stats.p95_ms < P95_TARGET_MS, (
            f"Price filter p95 ({stats.p95_ms:.0f}ms) exceeds target ({P95_TARGET_MS:.0f}ms)\n"
            f"Stats: {stats.to_dict()}"
        )

    async def test_location_filter_search_p95(
        self,
        authed_perf_client: AsyncClient,
    ) -> None:
        """Location-filtered search should have p95 < 2s."""
        measurements: list[float] = []
        query = {
            "query": "apartments",
            "filters": {
                "city": "Munich",
            },
            "limit": 10,
        }

        # Warmup
        for _ in range(WARMUP_REQUESTS):
            await authed_perf_client.post("/api/v1/search", json=query)

        # Benchmark
        for _ in range(BENCHMARK_REQUESTS):
            import time

            start = time.perf_counter()
            response = await authed_perf_client.post("/api/v1/search", json=query)
            elapsed = time.perf_counter() - start
            measurements.append(elapsed)
            assert response.status_code == 200

        stats = BenchmarkStats(measurements)

        assert stats.p95_ms < P95_TARGET_MS, (
            f"Location filter p95 ({stats.p95_ms:.0f}ms) exceeds target ({P95_TARGET_MS:.0f}ms)"
        )

    async def test_rooms_filter_search_p95(
        self,
        authed_perf_client: AsyncClient,
    ) -> None:
        """Rooms-filtered search should have p95 < 2s."""
        measurements: list[float] = []
        query = {
            "query": "apartments",
            "filters": {
                "rooms_min": 2,
                "rooms_max": 3,
            },
            "limit": 10,
        }

        # Warmup
        for _ in range(WARMUP_REQUESTS):
            await authed_perf_client.post("/api/v1/search", json=query)

        # Benchmark
        for _ in range(BENCHMARK_REQUESTS):
            import time

            start = time.perf_counter()
            response = await authed_perf_client.post("/api/v1/search", json=query)
            elapsed = time.perf_counter() - start
            measurements.append(elapsed)
            assert response.status_code == 200

        stats = BenchmarkStats(measurements)

        assert stats.p95_ms < P95_TARGET_MS, (
            f"Rooms filter p95 ({stats.p95_ms:.0f}ms) exceeds target ({P95_TARGET_MS:.0f}ms)"
        )

    async def test_combined_filters_search_p95(
        self,
        authed_perf_client: AsyncClient,
    ) -> None:
        """Combined filters should still meet p95 target."""
        measurements: list[float] = []
        query = {
            "query": "apartments",
            "filters": {
                "city": "Hamburg",
                "price_min": 100000,
                "price_max": 400000,
                "rooms_min": 2,
            },
            "limit": 10,
        }

        # Warmup
        for _ in range(WARMUP_REQUESTS):
            await authed_perf_client.post("/api/v1/search", json=query)

        # Benchmark
        for _ in range(BENCHMARK_REQUESTS):
            import time

            start = time.perf_counter()
            response = await authed_perf_client.post("/api/v1/search", json=query)
            elapsed = time.perf_counter() - start
            measurements.append(elapsed)
            assert response.status_code == 200

        stats = BenchmarkStats(measurements)

        assert stats.p95_ms < P95_TARGET_MS, (
            f"Combined filters p95 ({stats.p95_ms:.0f}ms) exceeds target ({P95_TARGET_MS:.0f}ms)"
        )


@pytest.mark.benchmark
@pytest.mark.asyncio
class TestComplexSearchBenchmark:
    """Benchmark tests for complex search queries with sorting and pagination."""

    async def test_sorted_search_p95(
        self,
        authed_perf_client: AsyncClient,
    ) -> None:
        """Sorted search should have p95 < 2s."""
        measurements: list[float] = []
        query = {
            "query": "apartments",
            "sort_by": "price",
            "sort_order": "asc",
            "limit": 20,
        }

        # Warmup
        for _ in range(WARMUP_REQUESTS):
            await authed_perf_client.post("/api/v1/search", json=query)

        # Benchmark
        for _ in range(BENCHMARK_REQUESTS):
            import time

            start = time.perf_counter()
            response = await authed_perf_client.post("/api/v1/search", json=query)
            elapsed = time.perf_counter() - start
            measurements.append(elapsed)
            assert response.status_code == 200

        stats = BenchmarkStats(measurements)

        assert stats.p95_ms < P95_TARGET_MS, (
            f"Sorted search p95 ({stats.p95_ms:.0f}ms) exceeds target ({P95_TARGET_MS:.0f}ms)"
        )

    async def test_paginated_search_p95(
        self,
        authed_perf_client: AsyncClient,
    ) -> None:
        """Paginated search should have p95 < 2s."""
        measurements: list[float] = []
        query = {
            "query": "apartments",
            "limit": 10,
            "offset": 20,
        }

        # Warmup
        for _ in range(WARMUP_REQUESTS):
            await authed_perf_client.post("/api/v1/search", json=query)

        # Benchmark
        for _ in range(BENCHMARK_REQUESTS):
            import time

            start = time.perf_counter()
            response = await authed_perf_client.post("/api/v1/search", json=query)
            elapsed = time.perf_counter() - start
            measurements.append(elapsed)
            assert response.status_code == 200

        stats = BenchmarkStats(measurements)

        assert stats.p95_ms < P95_TARGET_MS, (
            f"Paginated search p95 ({stats.p95_ms:.0f}ms) exceeds target ({P95_TARGET_MS:.0f}ms)"
        )

    async def test_complex_query_p95(
        self,
        authed_perf_client: AsyncClient,
    ) -> None:
        """Complex query with filters, sorting, and pagination should meet p95."""
        measurements: list[float] = []
        query = {
            "query": "luxury apartments",
            "filters": {
                "city": "Frankfurt",
                "price_min": 200000,
                "price_max": 800000,
                "rooms_min": 2,
            },
            "sort_by": "price",
            "sort_order": "desc",
            "limit": 15,
            "offset": 0,
        }

        # Warmup
        for _ in range(WARMUP_REQUESTS):
            await authed_perf_client.post("/api/v1/search", json=query)

        # Benchmark
        for _ in range(BENCHMARK_REQUESTS):
            import time

            start = time.perf_counter()
            response = await authed_perf_client.post("/api/v1/search", json=query)
            elapsed = time.perf_counter() - start
            measurements.append(elapsed)
            assert response.status_code == 200

        stats = BenchmarkStats(measurements)

        assert stats.p95_ms < P95_TARGET_MS, (
            f"Complex query p95 ({stats.p95_ms:.0f}ms) exceeds target ({P95_TARGET_MS:.0f}ms)\n"
            f"Stats: {stats.to_dict()}"
        )

    async def test_large_result_set_p95(
        self,
        authed_perf_client: AsyncClient,
    ) -> None:
        """Large result set should still meet p95 target."""
        measurements: list[float] = []
        query = {
            "query": "apartments",
            "limit": 50,  # Larger limit
        }

        # Warmup (fewer for large queries)
        for _ in range(3):
            await authed_perf_client.post("/api/v1/search", json=query)

        # Benchmark (fewer for large queries)
        for _ in range(25):  # Reduced for large result sets
            import time

            start = time.perf_counter()
            response = await authed_perf_client.post("/api/v1/search", json=query)
            elapsed = time.perf_counter() - start
            measurements.append(elapsed)
            assert response.status_code == 200

        stats = BenchmarkStats(measurements)

        # Allow slightly more lenient target for large results
        assert stats.p95_ms < P95_TARGET_MS * 1.2, (
            f"Large result p95 ({stats.p95_ms:.0f}ms) exceeds target ({P95_TARGET_MS * 1.2:.0f}ms)"
        )


@pytest.mark.benchmark
@pytest.mark.asyncio
class TestSearchBenchmarkSummary:
    """Generate summary benchmark report."""

    async def test_generate_benchmark_report(
        self,
        authed_perf_client: AsyncClient,
    ) -> None:
        """Generate a comprehensive benchmark report for search endpoints."""
        report: dict[str, Any] = {
            "target_p95_ms": P95_TARGET_MS,
            "target_avg_ms": AVG_TARGET_MS,
            "queries": {},
        }

        test_queries = [
            ("simple", {"query": "apartments in Berlin", "limit": 10}),
            (
                "price_filtered",
                {
                    "query": "apartments",
                    "filters": {"price_min": 100000, "price_max": 500000},
                    "limit": 10,
                },
            ),
            (
                "location_filtered",
                {"query": "apartments", "filters": {"city": "Munich"}, "limit": 10},
            ),
            (
                "sorted",
                {"query": "apartments", "sort_by": "price", "sort_order": "asc", "limit": 10},
            ),
        ]

        for name, query in test_queries:
            measurements: list[float] = []

            # Warmup
            for _ in range(WARMUP_REQUESTS):
                await authed_perf_client.post("/api/v1/search", json=query)

            # Benchmark
            for _ in range(BENCHMARK_REQUESTS):
                import time

                start = time.perf_counter()
                response = await authed_perf_client.post("/api/v1/search", json=query)
                elapsed = time.perf_counter() - start
                measurements.append(elapsed)
                assert response.status_code == 200

            stats = BenchmarkStats(measurements)
            report["queries"][name] = stats.to_dict()
            report["queries"][name]["passes_p95"] = stats.p95_ms < P95_TARGET_MS
            report["queries"][name]["passes_avg"] = stats.avg_ms < AVG_TARGET_MS

        # Overall summary
        all_pass_p95 = all(q["passes_p95"] for q in report["queries"].values())
        all_pass_avg = all(q["passes_avg"] for q in report["queries"].values())
        report["summary"] = {
            "all_queries_pass_p95": all_pass_p95,
            "all_queries_pass_avg": all_pass_avg,
        }

        # Print report for visibility
        print(f"\n{'=' * 60}")
        print("Search Benchmark Report")
        print(f"{'=' * 60}")
        print(f"Target p95: {P95_TARGET_MS:.0f}ms")
        print(f"Target avg: {AVG_TARGET_MS:.0f}ms")
        print(f"{'-' * 60}")
        for name, stats in report["queries"].items():
            status = "PASS" if stats["passes_p95"] else "FAIL"
            print(
                f"{name:20s} | p95: {stats['p95_ms']:6.0f}ms | avg: {stats['avg_ms']:6.0f}ms | {status}"
            )
        print(f"{'=' * 60}\n")

        assert all_pass_p95, "Some search queries did not meet p95 target"
