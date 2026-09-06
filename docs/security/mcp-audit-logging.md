# MCP Audit Logging System

This document describes the MCP (Model Context Protocol) audit logging system for connector operations.

## Overview

The MCP audit logging system provides comprehensive logging for all MCP connector operations, enabling:

- Security monitoring and incident response
- Compliance (SOC 2, GDPR)
- Performance analysis
- Debugging and troubleshooting

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   FastAPI       │────>│  MCP Connector   │────>│  External API   │
│   Request       │     │  (execute)       │     │                 │
└────────┬────────┘     └────────┬─────────┘     └─────────────────┘
         │                       │
         │                       ▼
         │              ┌──────────────────┐
         │              │  MCPAuditLogger  │
         │              │  (audit.py)      │
         │              └────────┬─────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐     ┌──────────────────┐
│  Request ID     │     │  CSV Log File    │
│  Context        │     │  (mcp_audit_)    │
│  (context.py)   │     └──────────────────┘
└─────────────────┘
```

## Components

### 1. MCPAuditLogger (`mcp/audit.py`)

Core audit logging class that writes structured events to CSV files.

```python
from mcp.audit import MCPAuditLogger, get_mcp_audit_logger

# Get singleton logger
logger = get_mcp_audit_logger()

# Log a connector call
logger.log_connector_call(
    connector_name="property_search",
    operation="search",
    params_meta={"query": "Berlin apartments", "limit": 10},
    result_meta={"count": 5, "execution_time_ms": 150},
    duration_ms=150,
    status="success",
)
```

### 2. Request ID Context (`mcp/context.py`)

Manages request ID propagation across async boundaries using `contextvars`.

```python
from mcp.context import MCPRequestContext, get_request_id

# Context manager (auto-generates ID)
async with MCPRequestContext() as ctx:
    print(f"Request ID: {ctx.request_id}")
    # All connector calls within this context share the same request_id

# Or with specific ID
async with MCPRequestContext(request_id="custom-123"):
    # Connector calls correlated with "custom-123"
    ...
```

### 3. Redaction Rules (`mcp/redaction.py`)

PII protection through pattern-based redaction.

**Automatically Redacted:**
- Email addresses
- API keys (sk-*, pk-*, etc.)
- Credit card numbers
- SSN
- Bearer tokens
- Passwords
- Connection strings

```python
from mcp.redaction import redact_params, sanitize_error_message

# Redact parameters before logging
safe_params = redact_params({
    "query": "test",
    "api_key": "sk-secret123",  # Will be redacted
})

# Sanitize error messages
safe_error = sanitize_error_message(
    "Failed with key sk-1234567890"
)
# Result: "Failed with key ***"
```

### 4. Retention Policy (`mcp/retention.py`)

Automatic cleanup of old audit logs.

```python
from mcp.retention import get_retention_manager

manager = get_retention_manager()

# Get storage metrics
metrics = manager.get_storage_metrics()
print(f"Files: {metrics['file_count']}, Size: {metrics['total_size_mb']}MB")

# Run cleanup (dry run first)
result = manager.cleanup(dry_run=True)
print(f"Would remove {result['files_found']} files")

# Actual cleanup
result = manager.cleanup(dry_run=False)
print(f"Removed {result['files_removed']} files")
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_AUDIT_LOGGING_ENABLED` | `true` | Enable/disable audit logging |
| `MCP_AUDIT_LOG_DIR` | `logs/mcp_audit` | Directory for audit logs |
| `MCP_AUDIT_RETENTION_DAYS` | `30` | Days to retain logs |

### Log File Format

Files are named: `mcp_audit_YYYY-MM-DD.csv`

**CSV Columns:**
- `timestamp` - ISO 8601 timestamp
- `event_type` - Event category (mcp.connector.execute, etc.)
- `level` - Severity (LOW, MEDIUM, HIGH, CRITICAL)
- `connector_name` - Name of connector
- `operation` - Operation performed
- `status` - Result status (success, failure, error)
- `duration_ms` - Execution duration
- `request_id` - Correlation ID
- `params_meta` - Redacted parameters
- `result_meta` - Redacted result
- `error_message` - Sanitized error if any
- `metadata` - Additional context

## API Endpoints

### Query Audit Logs

```http
GET /api/v1/admin/mcp/audit
Authorization: X-API-Key <key>

Query Parameters:
- connector_name: Filter by connector
- operation: Filter by operation
- status: Filter by status
- request_id: Filter by request ID
- start_date: ISO 8601 start date
- end_date: ISO 8601 end date
- limit: Max results (default 100)
- offset: Pagination offset
```

### Get Storage Metrics

```http
GET /api/v1/admin/mcp/audit/storage
Authorization: X-API-Key <key>

Response:
{
  "log_directory": "logs/mcp_audit",
  "file_count": 5,
  "total_size_bytes": 102400,
  "total_size_mb": 0.1,
  "oldest_log_date": "2026-03-01",
  "newest_log_date": "2026-03-23",
  "retention_days": 30,
  "expired_files": 0
}
```

### Run Cleanup

```http
POST /api/v1/admin/mcp/audit/cleanup
Authorization: X-API-Key <key>
Content-Type: application/json

{
  "dry_run": true
}
```

### Get Entries by Request ID

```http
GET /api/v1/admin/mcp/audit/request/{request_id}
Authorization: X-API-Key <key>
```

## Event Types

| Type | Description | Level |
|------|-------------|-------|
| `mcp.connector.connect` | Connector initialization | LOW |
| `mcp.connector.disconnect` | Connector cleanup | LOW |
| `mcp.connector.execute` | Successful operation | MEDIUM |
| `mcp.connector.error` | Operation error | HIGH |
| `mcp.connector.health_check` | Health check | LOW |
| `mcp.connector.allowlist_violation` | Allowlist bypass attempt | HIGH |

## Security Considerations

### PII Protection

1. **Automatic Redaction**: All PII is redacted before logging
2. **No Raw Data**: Only metadata is logged, not actual query/response data
3. **Error Sanitization**: Error messages are scrubbed of sensitive data

### Data Minimization

Only the following is logged:
- Connector name
- Operation type
- Parameter types (not values)
- Result types (not content)
- Duration
- Status
- Request ID for correlation

### Access Control

All audit API endpoints require:
- API key authentication (`X-API-Key` header)
- Admin privileges (recommended)

## Troubleshooting

### Audit Logs Not Being Created

1. Check `MCP_AUDIT_LOGGING_ENABLED` environment variable
2. Verify log directory exists and is writable
3. Check application logs for audit initialization message

### Disk Space Issues

1. Reduce retention days: `MCP_AUDIT_RETENTION_DAYS=7`
2. Run cleanup: `POST /api/v1/admin/mcp/audit/cleanup`
3. Consider moving logs to dedicated volume

### Missing Request Correlation

Ensure request ID is set in context before connector calls:

```python
from mcp.context import set_request_id

# In middleware
set_request_id(request.state.request_id)
```

## Best Practices

1. **Always use context**: Wrap connector operations in `MCPRequestContext`
2. **Redact early**: Redact params before logging, not after
3. **Monitor disk**: Set up alerts for disk usage on log directory
4. **Regular cleanup**: Schedule daily cleanup via cron or scheduler
5. **Review logs**: Periodically audit logs for security analysis
