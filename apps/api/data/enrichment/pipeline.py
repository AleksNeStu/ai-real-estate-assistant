"""
Enrichment Pipeline (Task #78).

This module orchestrates multiple enrichment providers for property data,
handling execution order, parallel processing, and result aggregation.

Features:
- Sequential and parallel execution modes
- Priority-based ordering
- Timeout handling
- Circuit breaker integration
- Result aggregation
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.security_utils import sanitize_for_log
from data.enrichment.cache import EnrichmentCache, get_enrichment_cache
from data.enrichment.hooks import (
    EnrichmentContext,
    EnrichmentResult,
    PropertyEnrichmentHook,
)
from data.enrichment.registry import EnrichmentRegistry
from data.enrichment.status import get_fallback_handler, get_status_tracker

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """Configuration for enrichment pipeline."""

    enabled: bool = True
    parallel_execution: bool = True
    max_concurrent: int = 5
    default_timeout: float = 30.0
    fail_fast: bool = False  # Stop on first error if True
    cache_enabled: bool = True
    fallback_on_error: bool = True
    sources: Optional[List[str]] = None  # None = all enabled sources


@dataclass
class PipelineResult:
    """Result of pipeline execution."""

    property_id: str
    results: Dict[str, EnrichmentResult] = field(default_factory=dict)
    enriched_fields: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    total_time_ms: float = 0.0

    @property
    def success(self) -> bool:
        """Check if all enrichments succeeded."""
        return len(self.errors) == 0

    @property
    def partial_success(self) -> bool:
        """Check if some enrichments succeeded."""
        return len(self.enriched_fields) > 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "property_id": self.property_id,
            "success": self.success,
            "partial_success": self.partial_success,
            "enriched_fields": self.enriched_fields,
            "errors": self.errors,
            "total_time_ms": self.total_time_ms,
            "results": {k: v.to_dict() for k, v in self.results.items()},
        }


class EnrichmentPipeline:
    """
    Orchestrates multiple enrichment providers for property data.

    Manages execution order, parallel processing, caching, and error handling.
    """

    def __init__(
        self,
        config: Optional[PipelineConfig] = None,
        cache: Optional[EnrichmentCache] = None,
    ):
        """
        Initialize enrichment pipeline.

        Args:
            config: Pipeline configuration
            cache: Optional cache instance
        """
        self._config = config or PipelineConfig()
        self._cache = cache or get_enrichment_cache()
        self._status_tracker = get_status_tracker()
        self._fallback_handler = get_fallback_handler()

    async def run(
        self,
        property_data: Dict[str, Any],
        sources: Optional[List[str]] = None,
    ) -> PipelineResult:
        """
        Run enrichment pipeline for a property.

        Args:
            property_data: Property data dictionary
            sources: Optional list of specific sources to run

        Returns:
            PipelineResult with enrichment results
        """
        import time

        start_time = time.perf_counter()

        context = EnrichmentContext.from_property(property_data)
        property_id = context.property_id

        result = PipelineResult(property_id=property_id)

        if not self._config.enabled:
            logger.info(
                "Enrichment pipeline disabled, skipping property %s", sanitize_for_log(property_id)
            )
            return result

        # Get enrichers to run
        enrichers = self._get_enrichers(sources)
        if not enrichers:
            logger.info("No enrichers available for property %s", sanitize_for_log(property_id))
            return result

        # Check cache first
        if self._config.cache_enabled:
            await self._check_cache(context, enrichers, result)

        # Get enrichers that still need to run
        pending_enrichers = [
            e
            for e in enrichers
            if f"{e.name}:{e.field}" not in result.results
            or not result.results[f"{e.name}:{e.field}"].success
        ]

        if not pending_enrichers:
            logger.info(
                "All enrichments served from cache for property %s", sanitize_for_log(property_id)
            )
            result.total_time_ms = (time.perf_counter() - start_time) * 1000
            return result

        # Run pending enrichers
        if self._config.parallel_execution:
            await self._run_parallel(context, pending_enrichers, result)
        else:
            await self._run_sequential(context, pending_enrichers, result)

        # Cache successful results
        if self._config.cache_enabled:
            self._cache_results(context, result)

        # Apply fallbacks for failures
        if self._config.fallback_on_error:
            self._apply_fallbacks(result)

        result.total_time_ms = (time.perf_counter() - start_time) * 1000
        return result

    def _get_enrichers(
        self,
        sources: Optional[List[str]] = None,
    ) -> List[PropertyEnrichmentHook]:
        """Get enrichers to run, respecting configuration."""
        source_filter = sources or self._config.sources

        if source_filter:
            enrichers = []
            for name in source_filter:
                enricher = EnrichmentRegistry.get_enricher(name)
                if enricher and enricher.is_enabled():
                    enrichers.append(enricher)
        else:
            enrichers = EnrichmentRegistry.get_all_enrichers(enabled_only=True)

        # Sort by priority
        enrichers.sort(key=lambda e: e.priority.value)
        return enrichers

    async def _check_cache(
        self,
        context: EnrichmentContext,
        enrichers: List[PropertyEnrichmentHook],
        result: PipelineResult,
    ) -> None:
        """Check cache for existing enrichment results."""
        for enricher in enrichers:
            cached = self._cache.get(
                enricher.name,
                context.property_id,
                enricher.field,
            )
            if cached:
                cached_result = EnrichmentResult.cached_result(
                    source=enricher.name,
                    enrichment_field=enricher.field,
                    value=cached.value,
                    ttl_seconds=cached.remaining_ttl(),
                )
                key = f"{enricher.name}:{enricher.field}"
                result.results[key] = cached_result
                result.enriched_fields[enricher.field] = cached.value

    async def _run_parallel(
        self,
        context: EnrichmentContext,
        enrichers: List[PropertyEnrichmentHook],
        result: PipelineResult,
    ) -> None:
        """Run enrichers in parallel with concurrency limit."""
        semaphore = asyncio.Semaphore(self._config.max_concurrent)

        async def run_with_semaphore(enricher: PropertyEnrichmentHook) -> None:
            async with semaphore:
                await self._run_enricher(context, enricher, result)

        tasks = [run_with_semaphore(e) for e in enrichers]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _run_sequential(
        self,
        context: EnrichmentContext,
        enrichers: List[PropertyEnrichmentHook],
        result: PipelineResult,
    ) -> None:
        """Run enrichers sequentially."""
        for enricher in enrichers:
            await self._run_enricher(context, enricher, result)

            # Check fail-fast
            if self._config.fail_fast and result.errors:
                logger.warning(
                    "Fail-fast triggered, stopping pipeline for property %s",
                    sanitize_for_log(context.property_id),
                )
                break

    async def _run_enricher(
        self,
        context: EnrichmentContext,
        enricher: PropertyEnrichmentHook,
        result: PipelineResult,
    ) -> None:
        """Run a single enricher and handle results."""
        key = f"{enricher.name}:{enricher.field}"

        try:
            # Run with timeout
            timeout = enricher.get_config().timeout_seconds or self._config.default_timeout

            enrichment_result = await asyncio.wait_for(
                enricher.enrich_with_timing(context),
                timeout=timeout,
            )

            result.results[key] = enrichment_result

            if enrichment_result.success:
                result.enriched_fields[enricher.field] = enrichment_result.value
                logger.debug(
                    "Enrichment succeeded: %s for property %s",
                    sanitize_for_log(enricher.name),
                    sanitize_for_log(context.property_id),
                )
            else:
                error_msg = enrichment_result.error or "Unknown error"
                result.errors.append(f"{enricher.name}: {error_msg}")
                logger.warning(
                    "Enrichment failed: %s for property %s - %s",
                    sanitize_for_log(enricher.name),
                    sanitize_for_log(context.property_id),
                    sanitize_for_log(error_msg),
                )

            # Update status tracker
            self._status_tracker.update(enrichment_result, context.property_id)

        except asyncio.TimeoutError:
            error_msg = f"Timeout after {timeout}s"
            timeout_result: EnrichmentResult = EnrichmentResult.error_result(
                source=enricher.name,
                enrichment_field=enricher.field,
                error=error_msg,
            )
            result.results[key] = timeout_result
            result.errors.append(f"{enricher.name}: {error_msg}")
            self._status_tracker.update(timeout_result, context.property_id)

        except Exception as e:
            error_msg = str(e)
            error_result: EnrichmentResult = EnrichmentResult.error_result(
                source=enricher.name,
                enrichment_field=enricher.field,
                error=error_msg,
            )
            result.results[key] = error_result
            result.errors.append(f"{enricher.name}: {error_msg}")
            self._status_tracker.update(error_result, context.property_id)

    def _cache_results(
        self,
        context: EnrichmentContext,
        result: PipelineResult,
    ) -> None:
        """Cache successful enrichment results."""
        for key, enrichment_result in result.results.items():
            if enrichment_result.success and not enrichment_result.cached:
                source, field = key.split(":", 1)
                self._cache.set(
                    source=source,
                    property_id=context.property_id,
                    enrichment_field=field,
                    value=enrichment_result.value,
                    ttl=enrichment_result.ttl_seconds,
                )

    def _apply_fallbacks(self, result: PipelineResult) -> None:
        """Apply fallback values for failed enrichments."""
        for key, enrichment_result in result.results.items():
            if not enrichment_result.success:
                source, field = key.split(":", 1)
                fallback_value = self._fallback_handler.get_fallback(
                    source=source,
                    field=field,
                    error=enrichment_result.error,
                )
                if fallback_value is not None:
                    result.enriched_fields[field] = fallback_value
                    logger.info("Applied fallback for %s", sanitize_for_log(field))

    async def run_batch(
        self,
        properties: List[Dict[str, Any]],
        sources: Optional[List[str]] = None,
    ) -> List[PipelineResult]:
        """
        Run enrichment pipeline for multiple properties.

        Args:
            properties: List of property data dictionaries
            sources: Optional list of specific sources to run

        Returns:
            List of PipelineResult objects
        """
        tasks = [self.run(prop, sources) for prop in properties]
        return await asyncio.gather(*tasks)

    def get_status(self, property_id: str) -> Dict[str, Any]:
        """
        Get enrichment status for a property.

        Args:
            property_id: Property identifier

        Returns:
            Status dictionary
        """
        return self._status_tracker.get_status(property_id)

    def invalidate_cache(self, property_id: str) -> int:
        """
        Invalidate cached enrichments for a property.

        Args:
            property_id: Property identifier

        Returns:
            Number of entries invalidated
        """
        return self._cache.invalidate_property(property_id)


# Global pipeline instance
_pipeline: Optional[EnrichmentPipeline] = None


def get_enrichment_pipeline(config: Optional[PipelineConfig] = None) -> EnrichmentPipeline:
    """
    Get the global enrichment pipeline instance.

    Args:
        config: Optional configuration override

    Returns:
        EnrichmentPipeline instance
    """
    global _pipeline
    if _pipeline is None or config:
        _pipeline = EnrichmentPipeline(config=config)
    return _pipeline
