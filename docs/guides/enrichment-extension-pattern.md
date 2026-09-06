# Property Enrichment Extension Pattern

This document describes how to create custom property enrichment hooks for the AI Real Estate Assistant.

## Overview

The enrichment system allows augmenting property data with additional information from external sources (air quality, safety scores, transport data, etc.) during ingestion or on-demand.

## Architecture

```
Property Data
     ↓
EnrichmentPipeline
     ↓
┌────────────────────────────────────┐
│  EnrichmentRegistry                │
│  ├── AirQualityEnricher            │
│  ├── SafetyScoreEnricher           │
│  └── CustomEnricher                │
└────────────────────────────────────┘
     ↓
EnrichmentCache (Redis + in-memory fallback)
     ↓
Enriched Property
```

## Creating a Custom Enricher

### 1. Create the Enricher Class

```python
from data.enrichment.hooks import (
    EnrichmentConfig,
    EnrichmentContext,
    EnrichmentPriority,
    EnrichmentResult,
    PropertyEnrichmentHook,
)
from data.enrichment.registry import register_enricher
import os


@register_enricher
class CustomEnricher(PropertyEnrichmentHook[dict]):
    """Enrichment provider for custom data."""

    # Required: unique identifier
    name = "custom_enricher"

    # Optional: display name for UI
    display_name = "Custom Data Provider"

    # Optional: description
    description = "Fetches custom data from external API"

    # Required: property field to enrich
    field = "custom_data"

    # Optional: whether API key is required
    requires_api_key = True
    api_key_env_var = "CUSTOM_API_KEY"

    # Optional: default configuration
    default_timeout = 15.0
    default_ttl = 3600  # 1 hour
    priority = EnrichmentPriority.NORMAL

    async def enrich(self, context: EnrichmentContext) -> EnrichmentResult:
        """
        Fetch enrichment data for a property.

        Args:
            context: Property context with location data

        Returns:
            EnrichmentResult with the fetched data
        """
        # Check for required data
        if not context.latitude or not context.longitude:
            return EnrichmentResult.skipped_result(
                source=self.name,
                field=self.field,
                reason="Missing coordinates",
            )

        try:
            # Fetch data from external API
            api_key = os.getenv(self.api_key_env_var)
            data = await self._fetch_data(
                lat=context.latitude,
                lon=context.longitude,
                api_key=api_key,
            )

            return EnrichmentResult.success_result(
                source=self.name,
                field=self.field,
                value=data,
                ttl_seconds=self._config.ttl_seconds,
            )

        except Exception as e:
            return EnrichmentResult.error_result(
                source=self.name,
                field=self.field,
                error=str(e),
            )

    async def health_check(self) -> bool:
        """Check if the external service is available."""
        try:
            # Make a test request
            return True
        except Exception:
            return False

    async def _fetch_data(self, lat: float, lon: float, api_key: str) -> dict:
        """Fetch data from external API."""
        # Implementation details...
        return {"data": "value"}
```

### 2. Register the Enricher

Enrichers are automatically registered when using the `@register_enricher` decorator. The module must be imported at startup.

Add to `apps/api/data/enrichment/enrichers/__init__.py`:

```python
from data.enrichment.enrichers.custom_enricher import CustomEnricher

__all__ = [
    # ... existing enrichers
    "CustomEnricher",
]
```

### 3. Configure (Optional)

Add configuration to `apps/api/config/settings.py`:

```python
custom_api_key: Optional[str] = Field(
    default_factory=lambda: os.getenv("CUSTOM_API_KEY"),
    description="API key for custom enrichment provider",
)
```

## Enrichment Context

The `EnrichmentContext` provides property data for enrichment:

```python
@dataclass
class EnrichmentContext:
    property_id: str
    address: Optional[str]
    city: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    postal_code: Optional[str]
    country: Optional[str]
    extra: Dict[str, Any]  # All other property fields
```

## Enrichment Results

### Success

```python
EnrichmentResult.success_result(
    source="enricher_name",
    field="field_name",
    value={"data": "value"},
    ttl_seconds=3600,
)
```

### From Cache

```python
EnrichmentResult.cached_result(
    source="enricher_name",
    field="field_name",
    value={"data": "value"},
    ttl_seconds=remaining_ttl,
)
```

### Error

```python
EnrichmentResult.error_result(
    source="enricher_name",
    field="field_name",
    error="Error message",
)
```

### Skipped

```python
EnrichmentResult.skipped_result(
    source="enricher_name",
    field="field_name",
    reason="Missing required data",
)
```

## Configuration

### Per-Enricher Configuration

```python
from data.enrichment.registry import EnrichmentRegistry
from data.enrichment.hooks import EnrichmentConfig

EnrichmentRegistry.set_config(
    "custom_enricher",
    EnrichmentConfig(
        enabled=True,
        ttl_seconds=7200,
        timeout_seconds=60.0,
        priority=EnrichmentPriority.HIGH,
        required=False,
        fallback_value={"default": "value"},
    ),
)
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ENRICHMENT_ENABLED` | Enable enrichment system | `false` |
| `ENRICHMENT_DEFAULT_TTL` | Default cache TTL (seconds) | `3600` |
| `ENRICHMENT_PARALLEL_EXECUTION` | Run enrichers in parallel | `true` |
| `ENRICHMENT_MAX_CONCURRENT` | Max concurrent enrichers | `5` |
| `ENRICHMENT_TIMEOUT_SECONDS` | Default timeout | `30` |
| `ENRICHMENT_SOURCES` | Enabled sources (comma-separated) | all |
| `ENRICHMENT_CACHE_ENABLED` | Enable caching | `true` |
| `ENRICHMENT_FALLBACK_ON_ERROR` | Use fallback values on error | `true` |

## Using the Pipeline

### Basic Usage

```python
from data.enrichment.pipeline import get_enrichment_pipeline

pipeline = get_enrichment_pipeline()

result = await pipeline.run({
    "id": "property-123",
    "city": "Berlin",
    "latitude": 52.5200,
    "longitude": 13.4050,
})

print(result.enriched_fields)
# {"air_quality_index": 42, "safety_score": 8.5}
```

### With Specific Sources

```python
result = await pipeline.run(
    property_data,
    sources=["air_quality", "safety_score"],
)
```

### Batch Processing

```python
results = await pipeline.run_batch([
    {"id": "prop-1", "city": "Berlin"},
    {"id": "prop-2", "city": "Munich"},
])
```

## Testing

### Unit Tests

```python
import pytest
from data.enrichment.hooks import EnrichmentContext, EnrichmentResult
from data.enrichment.enrichers.custom import CustomEnricher


@pytest.mark.asyncio
async def test_custom_enricher():
    enricher = CustomEnricher()
    context = EnrichmentContext(
        property_id="test",
        latitude=52.5200,
        longitude=13.4050,
    )

    result = await enricher.enrich(context)

    assert result.success
    assert result.field == "custom_data"
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_pipeline_with_custom_enricher():
    from data.enrichment.registry import EnrichmentRegistry
    from data.enrichment.pipeline import EnrichmentPipeline

    EnrichmentRegistry.register(CustomEnricher)

    pipeline = EnrichmentPipeline()
    result = await pipeline.run({"id": "test"})

    assert "custom_data" in result.enriched_fields
```

## Best Practices

1. **Graceful Degradation**: Always handle missing data and API failures gracefully
2. **Caching**: Use appropriate TTLs based on data freshness requirements
3. **Timeouts**: Set reasonable timeouts to avoid blocking the pipeline
4. **Rate Limiting**: Respect external API rate limits
5. **Logging**: Log errors and important events for debugging
6. **Health Checks**: Implement meaningful health checks for monitoring
7. **Testing**: Write comprehensive unit and integration tests

## Error Handling

The enrichment system handles errors gracefully:

1. **Skipped**: Missing required data (coordinates, city, etc.)
2. **Failed**: API errors, timeouts, exceptions
3. **Fallback**: Optional fallback values when enabled

```python
# Fallback configuration
EnrichmentConfig(
    fallback_value={"default": "value"},
    fallback_on_error=True,
)
```

## Monitoring

Check enrichment status:

```python
from data.enrichment.status import get_status_tracker

tracker = get_status_tracker()
status = tracker.get_status("property-123")

# {
#   "property_id": "property-123",
#   "enrichments": {
#     "air_quality:air_quality_index": {
#       "status": "completed",
#       "value": 42,
#       "cached": true,
#     }
#   },
#   "summary": {"total": 1, "status_counts": {"completed": 1}}
# }
```
