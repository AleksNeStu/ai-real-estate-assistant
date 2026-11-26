# AI Real Estate Assistant API Documentation

This is the official API documentation for the AI Real Estate Assistant backend service.

## Base URL

```
http://localhost:8000
```

In production, use the configured domain.

## API Version

Current API version: `v1`

All endpoints are prefixed with `/api/v1/`.

## Authentication

The API supports multiple authentication methods:

1. **API Key Authentication** - For backend services and general API access
2. **JWT Authentication** - For user-specific features (favorites, saved searches, etc.)

See [Authentication](authentication.md) for detailed documentation.

## Interactive Documentation

When the API is running, you can access:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI Schema**: `http://localhost:8000/openapi.json`

Endpoints are organized by tag in Swagger UI (Search, Chat, Tools, Market Analytics, etc.).

To regenerate the static OpenAPI schema:

```bash
cd apps/api && python -m scripts.docs.export_openapi
```

## The contract is checked on every pull request

The `api-contract` job of the pipeline compares the schema the application
serves with the baseline that was released (`docs/api-v1-baseline.json`), and
it fails on a difference a consumer cannot survive: a field that is gone,
renamed, retyped or newly required, an endpoint or a parameter that
disappeared. An additive change passes - a consumer that does not know the
new field ignores it.

The same check runs locally:

```bash
python scripts/api/openapi_diff.py
```

To accept a change of the contract on purpose, move the baseline with the
command the failure names:

```bash
python scripts/api/openapi_diff.py --update-baseline
```

## Available Resources

| Resource | Description | Auth Required |
|----------|-------------|---------------|
| [Search](properties.md#property-search) | Semantic property search with filters | API Key |
| [Chat](properties.md#conversational-ai) | AI-powered property assistant | API Key |
| [RAG](properties.md#retrieval-augmented-generation) | Document Q&A with citations | API Key |
| [Market](market.md) | Price history and market trends | JWT |
| [Favorites](favorites.md) | Property favorites/watchlist | JWT |
| [Collections](favorites.md#collections) | Organize favorites into collections | JWT |
| [Saved Searches](favorites.md#saved-searches) | Save searches with alert settings | JWT |
| [Tools](properties.md#calculation-tools) | Mortgage, investment, TCO calculators | API Key |
| [Admin](properties.md#administration) | Data ingestion and reindexing | Admin identity |
| [Export](properties.md#data-export) | Export properties to various formats | API Key |

## Rate Limiting

- **Default**: 100 requests per minute per IP
- **Auth endpoints**: 3-5 requests per minute (stricter limits)
- Rate limit headers are included in all responses:
  - `X-RateLimit-Limit`: Request limit
  - `X-RateLimit-Remaining`: Remaining requests
  - `X-RateLimit-Reset`: Unix timestamp when limit resets

## Request Headers

### Standard Headers

```http
Content-Type: application/json
Accept: application/json
```

### API Key Authentication

```http
X-API-Key: $API_KEY
```

### JWT Authentication

```http
Authorization: Bearer $JWT_TOKEN
```

### Optional Headers

```http
X-User-Email: user@example.com  # Set LLM model preferences per user
X-Request-ID: custom-request-id  # Custom request ID for tracing
```

## Response Format

All API responses follow this structure:

### Success Response

```json
{
  "field1": "value1",
  "field2": "value2"
}
```

### Error Response

```json
{
  "detail": "Error message describing what went wrong"
}
```

## Pagination

List endpoints support pagination via query parameters:

```
?limit=50&offset=0
```

- `limit`: Number of items to return (default: varies by endpoint, max: 100)
- `offset`: Number of items to skip (default: 0)

## Filtering

Many endpoints support filtering via query parameters. The exact filters available depend on the endpoint.

Example:
```
?city=Berlin&min_price=100000&max_price=500000
```

## Sorting

Search and list endpoints support sorting:

```
?sort_by=price&sort_order=asc
```

Available sort fields vary by endpoint.

## Health Check

Check API status without authentication:

```http
GET /health
```

Response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-15T10:30:00Z",
  "uptime_seconds": 3600,
  "dependencies": {
    "vector_store": {
      "status": "healthy",
      "message": "Connected",
      "latency_ms": 5
    },
    "database": {
      "status": "healthy",
      "message": "Connected",
      "latency_ms": 2
    }
  }
}
```

## Error Codes

| HTTP Code | Description |
|-----------|-------------|
| 200 | Success |
| 201 | Created |
| 204 | No Content |
| 400 | Bad Request - Invalid input |
| 401 | Unauthorized - Missing or invalid credentials |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource doesn't exist |
| 409 | Conflict - Resource already exists |
| 413 | Payload Too Large |
| 422 | Unprocessable Entity |
| 423 | Locked - Account temporarily locked |
| 429 | Too Many Requests |
| 500 | Internal Server Error |
| 503 | Service Unavailable - Required service offline |

See [Error Handling](errors.md) for detailed error documentation.

## SDKs and Libraries

Official SDKs:

- **Python**: Coming soon
- **JavaScript/TypeScript**: Coming soon
- **cURL examples**: Provided in documentation

## Support

For API support:
- GitHub Issues: https://github.com/AleksNeStu/ai-real-estate-assistant/issues
- GitHub Discussions: https://github.com/AleksNeStu/ai-real-estate-assistant/discussions
- Documentation: https://github.com/AleksNeStu/ai-real-estate-assistant/tree/main/docs

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 15.01.2024 | Initial release |
