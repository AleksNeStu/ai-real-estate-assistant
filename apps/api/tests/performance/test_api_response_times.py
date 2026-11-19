"""API Response Time Benchmark Tests.

Tests API endpoints against defined performance thresholds:
- Search API: p95 < 2s
- Chat API: p95 < 8s (includes LLM processing)
- Document upload: < 5s for 10MB
- Health check: p95 < 100ms
"""

import os
import time

import pytest
from httpx import AsyncClient

from tests.performance.conftest import (
    PerformanceMetrics,
    concurrent_requests,
    measure_request,
)

# Number of requests for statistical significance
WARMUP_REQUESTS = 5
MEASUREMENT_REQUESTS = 50
CONCURRENT_USERS = 10


@pytest.mark.performance
@pytest.mark.asyncio
class TestHealthEndpointPerformance:
    """Performance tests for health endpoint."""

    async def test_health_endpoint_response_time(
        self,
        perf_client: AsyncClient,
        metrics: PerformanceMetrics,
        performance_thresholds: dict,
    ):
        """Health endpoint should respond within 100ms (p95)."""
        threshold = performance_thresholds["health"]

        # Warmup
        for _ in range(WARMUP_REQUESTS):
            await perf_client.get("/health")

        # Measurement
        for _ in range(MEASUREMENT_REQUESTS):
            await measure_request(perf_client, "GET", "/health", metrics)

        # Assertions
        assert metrics.p95 < threshold["p95_max"], (
            f"Health endpoint p95 ({metrics.p95:.3f}s) exceeds threshold ({threshold['p95_max']}s)"
        )
        assert metrics.success_rate >= threshold["success_rate_min"], (
            f"Health endpoint success rate ({metrics.success_rate:.2f}%) "
            f"below threshold ({threshold['success_rate_min']}%)"
        )

    async def test_health_endpoint_concurrent(
        self,
        perf_client: AsyncClient,
        metrics: PerformanceMetrics,
    ):
        """Health endpoint should handle concurrent requests."""
        await concurrent_requests(perf_client, "GET", "/health", CONCURRENT_USERS, metrics)

        assert metrics.success_rate >= 99.0, (
            f"Concurrent health check success rate ({metrics.success_rate:.2f}%) below 99%"
        )
        assert metrics.p95 < 0.2, f"Concurrent health check p95 ({metrics.p95:.3f}s) exceeds 200ms"


@pytest.mark.performance
@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.environ.get("RUN_INTEGRATION_TESTS"),
    reason="Integration tests require running server and API key",
)
class TestSearchAPIPerformance:
    """Performance tests for search endpoints."""

    async def test_property_search_response_time(
        self,
        authed_perf_client: AsyncClient,
        metrics: PerformanceMetrics,
        performance_thresholds: dict,
    ):
        """Property search should respond within 2s (p95)."""
        threshold = performance_thresholds["search"]
        search_payload = {"query": "apartments in Berlin", "limit": 10}

        # Warmup
        for _ in range(WARMUP_REQUESTS):
            await authed_perf_client.post("/api/v1/search", json=search_payload)

        # Measurement
        for _ in range(MEASUREMENT_REQUESTS):
            await measure_request(
                authed_perf_client,
                "POST",
                "/api/v1/search",
                metrics,
                json=search_payload,
            )

        # Assertions
        assert metrics.p95 < threshold["p95_max"], (
            f"Search API p95 ({metrics.p95:.3f}s) exceeds threshold ({threshold['p95_max']}s)"
        )
        assert metrics.avg < threshold["avg_max"], (
            f"Search API avg ({metrics.avg:.3f}s) exceeds threshold ({threshold['avg_max']}s)"
        )

    async def test_property_search_concurrent(
        self,
        authed_perf_client: AsyncClient,
        metrics: PerformanceMetrics,
    ):
        """Search API should handle concurrent requests."""
        search_payload = {"query": "2-bedroom apartment", "limit": 5}

        await concurrent_requests(
            authed_perf_client,
            "POST",
            "/api/v1/search",
            CONCURRENT_USERS,
            metrics,
            json=search_payload,
        )

        assert metrics.success_rate >= 95.0, (
            f"Concurrent search success rate ({metrics.success_rate:.2f}%) below 95%"
        )

    async def test_property_list_response_time(
        self,
        authed_perf_client: AsyncClient,
        metrics: PerformanceMetrics,
        performance_thresholds: dict,
    ):
        """Property list should respond within threshold."""
        threshold = performance_thresholds["search"]

        # Warmup
        for _ in range(WARMUP_REQUESTS):
            await authed_perf_client.get("/api/v1/properties")

        # Measurement
        for _ in range(MEASUREMENT_REQUESTS):
            await measure_request(authed_perf_client, "GET", "/api/v1/properties", metrics)

        assert metrics.p95 < threshold["p95_max"], (
            f"Property list p95 ({metrics.p95:.3f}s) exceeds threshold"
        )


@pytest.mark.performance
@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.environ.get("RUN_INTEGRATION_TESTS"),
    reason="Integration tests require running server and API key",
)
class TestChatAPIPerformance:
    """Performance tests for chat endpoints."""

    async def test_chat_message_response_time(
        self,
        authed_perf_client: AsyncClient,
        metrics: PerformanceMetrics,
        performance_thresholds: dict,
    ):
        """Chat API should respond within 8s (p95, includes LLM processing)."""
        threshold = performance_thresholds["chat"]
        chat_payload = {
            "message": "What properties are available in Munich?",
            "session_id": "perf-test-session",
        }

        # Warmup (fewer requests due to LLM latency)
        for _ in range(2):
            await authed_perf_client.post("/api/v1/chat", json=chat_payload)

        # Measurement (fewer requests for chat)
        for _ in range(10):
            await measure_request(
                authed_perf_client, "POST", "/api/v1/chat", metrics, json=chat_payload
            )

        # Assertions
        assert metrics.p95 < threshold["p95_max"], (
            f"Chat API p95 ({metrics.p95:.3f}s) exceeds threshold ({threshold['p95_max']}s)"
        )
        assert metrics.success_rate >= threshold["success_rate_min"], (
            f"Chat API success rate ({metrics.success_rate:.2f}%) "
            f"below threshold ({threshold['success_rate_min']}%)"
        )

    async def test_chat_simple_query_performance(
        self,
        authed_perf_client: AsyncClient,
        metrics: PerformanceMetrics,
    ):
        """Simple queries should be faster than complex ones."""
        simple_payload = {
            "message": "Hello",
            "session_id": "perf-simple-test",
        }

        for _ in range(5):
            await measure_request(
                authed_perf_client,
                "POST",
                "/api/v1/chat",
                metrics,
                json=simple_payload,
            )

        # Simple queries should be faster than the general threshold
        assert metrics.avg < 3.0, f"Simple chat query avg ({metrics.avg:.3f}s) exceeds 3s"


@pytest.mark.performance
@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.environ.get("RUN_INTEGRATION_TESTS"),
    reason="Integration tests require running server and API key",
)
class TestDocumentAPIPerformance:
    """Performance tests for document endpoints."""

    async def test_document_upload_small_file(
        self,
        authed_perf_client: AsyncClient,
        metrics: PerformanceMetrics,
        performance_thresholds: dict,
    ):
        """Small document upload should complete quickly."""
        threshold = performance_thresholds["documents"]

        # Create a small test file (100KB)
        small_file = b"Test document content\n" * 5000

        for _ in range(5):
            files = {"file": ("test.txt", small_file, "text/plain")}
            await measure_request(
                authed_perf_client,
                "POST",
                "/api/v1/documents/upload",
                metrics,
                files=files,
            )

        assert metrics.avg < threshold["avg_max"], (
            f"Small document upload avg ({metrics.avg:.3f}s) exceeds threshold"
        )

    async def test_document_list_response_time(
        self,
        authed_perf_client: AsyncClient,
        metrics: PerformanceMetrics,
        performance_thresholds: dict,
    ):
        """Document list should respond quickly."""
        _threshold = performance_thresholds["documents"]

        # Warmup
        for _ in range(WARMUP_REQUESTS):
            await authed_perf_client.get("/api/v1/documents")

        # Measurement
        for _ in range(MEASUREMENT_REQUESTS):
            await measure_request(authed_perf_client, "GET", "/api/v1/documents", metrics)

        assert metrics.p95 < 1.0, f"Document list p95 ({metrics.p95:.3f}s) exceeds 1s"


@pytest.mark.performance
@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.environ.get("RUN_INTEGRATION_TESTS"),
    reason="Integration tests require running server and API key",
)
class TestLeadsAPIPerformance:
    """Performance tests for leads endpoints."""

    async def test_leads_list_response_time(
        self,
        authed_perf_client: AsyncClient,
        metrics: PerformanceMetrics,
        performance_thresholds: dict,
    ):
        """Leads list should respond within threshold."""
        threshold = performance_thresholds["leads"]

        # Warmup
        for _ in range(WARMUP_REQUESTS):
            await authed_perf_client.get("/api/v1/leads")

        # Measurement
        for _ in range(MEASUREMENT_REQUESTS):
            await measure_request(authed_perf_client, "GET", "/api/v1/leads", metrics)

        assert metrics.p95 < threshold["p95_max"], (
            f"Leads list p95 ({metrics.p95:.3f}s) exceeds threshold"
        )
        assert metrics.success_rate >= threshold["success_rate_min"], (
            f"Leads list success rate ({metrics.success_rate:.2f}%) below threshold"
        )

    async def test_lead_creation_performance(
        self,
        authed_perf_client: AsyncClient,
        metrics: PerformanceMetrics,
    ):
        """Lead creation should be fast."""
        lead_payload = {
            "name": f"Test Lead {time.time()}",
            "email": f"test{time.time()}@example.com",
            "phone": "+49123456789",
            "interest": "apartment",
        }

        for _ in range(10):
            await measure_request(
                authed_perf_client,
                "POST",
                "/api/v1/leads",
                metrics,
                json=lead_payload,
            )

        assert metrics.avg < 0.5, f"Lead creation avg ({metrics.avg:.3f}s) exceeds 500ms"


@pytest.mark.performance
@pytest.mark.asyncio
class TestMetricsCollection:
    """Tests for metrics collection and reporting."""

    async def test_performance_metrics_collection(
        self,
        perf_client: AsyncClient,
        metrics: PerformanceMetrics,
    ):
        """Should correctly collect and calculate metrics."""
        # Make some requests
        for _ in range(10):
            await measure_request(perf_client, "GET", "/health", metrics)

        # Verify metrics
        assert metrics.total_requests == 10
        assert metrics.success_rate == 100.0
        assert metrics.min <= metrics.avg <= metrics.max
        assert metrics.p50 <= metrics.p95 <= metrics.p99

    async def test_metrics_to_dict(
        self,
        perf_client: AsyncClient,
        metrics: PerformanceMetrics,
    ):
        """Should serialize metrics to dictionary."""
        for _ in range(5):
            await measure_request(perf_client, "GET", "/health", metrics)

        result = metrics.to_dict()

        assert "total_requests" in result
        assert "success_rate" in result
        assert "response_times" in result
        assert "status_codes" in result
        assert result["total_requests"] == 5
