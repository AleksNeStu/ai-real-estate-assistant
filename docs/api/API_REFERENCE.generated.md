# API Reference (Generated)

This file is generated from the committed OpenAPI schema snapshot (`docs/api/openapi.json`).
- Source title: AI Real Estate Assistant - Modern
- Source version: 1.0.0

To regenerate:

```powershell
python scripts\docs\export_openapi.py
python scripts\docs\generate_api_reference.py
```

---

## GET /api/v1/admin/dashboard

**Summary**: Admin Dashboard

**Tags**: Admin

Aggregated admin dashboard endpoint (Task #67). Combines health, cache, latency, vector store, and system stats into a single JSON response for frontend admin panel consumption.

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | object |

## POST /api/v1/admin/excel/sheets

**Summary**: Get Excel Sheets

**Tags**: Admin

Get sheet names from an Excel file. Returns available sheets and their row counts for sheet selection UI.

**Request Body**

- Required: yes
- application/json: ExcelSheetsRequest

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | ExcelSheetsResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/admin/excel/sheets/upload

**Summary**: Get Excel Sheets Upload

**Tags**: Admin

Get sheet names from an uploaded Excel file. Returns available sheets and their row counts for sheet selection UI. Supports: .xlsx, .xls, .ods files.

**Request Body**

- Required: yes
- multipart/form-data: Body_get_excel_sheets_upload_api_v1_admin_excel_sheets_upload_post

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | ExcelSheetsResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/admin/health

**Summary**: Admin Health Check

**Tags**: Admin

Detailed health check for admin.

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | HealthCheck |

## POST /api/v1/admin/ingest

**Summary**: Ingest Data

**Tags**: Admin

Trigger data ingestion from URLs. Downloads CSV/Excel files, processes them, and saves to local cache. Does NOT automatically reindex vector store (call /reindex for that). Enforces max_properties limit from settings.

**Request Body**

- Required: yes
- application/json: IngestRequest

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | IngestResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/admin/ingest/upload

**Summary**: Ingest File Upload

**Tags**: Admin

Upload and ingest property data from Excel/CSV files. Supports: .xlsx, .xls, .ods, .csv files. Maximum file size: 25MB. Does NOT automatically reindex vector store (call /reindex for that).

**Request Body**

- Required: yes
- multipart/form-data: Body_ingest_file_upload_api_v1_admin_ingest_upload_post

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | IngestResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/admin/mcp/audit

**Summary**: List Audit Entries

**Tags**: MCP Audit

Query MCP audit logs with filters. Requires API key authentication. Returns paginated audit log entries matching the specified filters.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| connector_name | query | string \| null | no | Filter by connector name |
| operation | query | string \| null | no | Filter by operation |
| status | query | string \| null | no | Filter by status (success, failure, error) |
| request_id | query | string \| null | no | Filter by request ID |
| start_date | query | string \| null | no | Filter by start date (ISO 8601) |
| end_date | query | string \| null | no | Filter by end date (ISO 8601) |
| limit | query | integer | no | Maximum results to return |
| offset | query | integer | no | Offset for pagination |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | AuditListResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/admin/mcp/audit/cleanup

**Summary**: Run Cleanup

**Tags**: MCP Audit

Run cleanup of expired MCP audit logs. Requires API key authentication. By default, runs in dry-run mode (no files deleted). Set dry_run=false to actually delete files.

**Request Body**

- Required: yes
- application/json: CleanupRequest

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | CleanupResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/admin/mcp/audit/connector/{connector_name}

**Summary**: Get Entries By Connector

**Tags**: MCP Audit

Get audit entries for a specific connector. Requires API key authentication. Returns paginated entries for the specified connector.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| connector_name | path | string | yes |  |
| limit | query | integer | no |  |
| offset | query | integer | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | AuditListResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/admin/mcp/audit/request/{request_id}

**Summary**: Get Entries By Request Id

**Tags**: MCP Audit

Get all audit entries for a specific request ID. Requires API key authentication. Useful for tracing a request through multiple connector calls.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| request_id | path | string | yes |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | array[object] |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/admin/mcp/audit/storage

**Summary**: Get Storage Metrics

**Tags**: MCP Audit

Get storage metrics for MCP audit logs. Requires API key authentication. Returns information about log file storage including: - Number of files - Total size - Date range - Expired files count

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | StorageMetricsResponse |

## GET /api/v1/admin/metrics

**Summary**: Admin Metrics

**Tags**: Admin

Return comprehensive API metrics for monitoring dashboard.

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | object |

## GET /api/v1/admin/metrics/latency

**Summary**: Admin Latency Metrics

**Tags**: Admin

Return p95 latency metrics for search and chat endpoints (Task #120). SLA targets: - search: p95 < 2000 ms - chat: p95 < 8000 ms

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | object |

## GET /api/v1/admin/notifications-stats

**Summary**: Admin Notifications Stats

**Tags**: Admin

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | NotificationsAdminStats |

## GET /api/v1/admin/portals

**Summary**: List Portals

**Tags**: Admin

List all available portal adapters. Returns information about each portal including: - Whether it's configured (has API key if required) - Rate limit information

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | PortalAdaptersResponse |

## POST /api/v1/admin/portals/fetch

**Summary**: Fetch From Portal

**Tags**: Admin

Fetch property data from an external portal. Uses the specified portal adapter to fetch properties based on filters. The fetched data is automatically ingested into the property cache.

**Request Body**

- Required: yes
- application/json: PortalFiltersRequest

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | PortalIngestResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/admin/reindex

**Summary**: Reindex Data

**Tags**: Admin

Reindex data from cache to vector store.

**Request Body**

- Required: yes
- application/json: ReindexRequest

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | ReindexResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/admin/version

**Summary**: Admin Version Info

**Tags**: Admin

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | AdminVersionInfo |

## GET /api/v1/agent-analytics/deals

**Summary**: List my deals

**Tags**: Agent Analytics

List deals for the current agent with optional filtering.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| status | query | string \| null | no | Filter by deal status |
| page | query | integer | no | Page number |
| page_size | query | integer | no | Items per page |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | DealListResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/agent-analytics/deals

**Summary**: Create deal

**Tags**: Agent Analytics

Create a new deal when a lead converts.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| access_token | cookie | string \| null | no |  |

**Request Body**

- Required: yes
- application/json: DealCreate

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 201 | Successful Response | DealResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/agent-analytics/deals/{deal_id}

**Summary**: Get deal details

**Tags**: Agent Analytics

Get detailed information about a specific deal.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| deal_id | path | string | yes |  |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | DealResponse |
| 422 | Validation Error | HTTPValidationError |

## PATCH /api/v1/agent-analytics/deals/{deal_id}

**Summary**: Update deal

**Tags**: Agent Analytics

Update deal status and other fields.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| deal_id | path | string | yes |  |
| access_token | cookie | string \| null | no |  |

**Request Body**

- Required: yes
- application/json: DealUpdate

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | DealResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/agent-analytics/me

**Summary**: Get my performance metrics

**Tags**: Agent Analytics

Get comprehensive performance metrics for the current agent including leads, deals, conversion rates, and financial data.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| period_start | query | string \| null | no | Start of analysis period (default: 30 days ago) |
| period_end | query | string \| null | no | End of analysis period (default: now) |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | AgentMetricsResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/agent-analytics/me/comparison

**Summary**: Get team comparison

**Tags**: Agent Analytics

Compare current agent's performance to team averages with rankings.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| period_start | query | string \| null | no |  |
| period_end | query | string \| null | no |  |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | TeamComparisonResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/agent-analytics/me/goals

**Summary**: Get goal progress

**Tags**: Agent Analytics

Get progress towards active goals.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | GoalProgressListResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/agent-analytics/me/insights

**Summary**: Get coaching insights

**Tags**: Agent Analytics

Get AI-powered coaching insights with actionable recommendations.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | CoachingInsightsResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/agent-analytics/me/trends

**Summary**: Get performance trends

**Tags**: Agent Analytics

Get performance trends over time with configurable intervals.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| interval | query | string | no | Time interval |
| periods | query | integer | no | Number of periods to return |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | PerformanceTrendsResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/agent-analytics/needs-support

**Summary**: Get agents needing support

**Tags**: Agent Analytics

Identify agents who may need coaching support (admin only).

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| threshold_days | query | integer | no | Days without deal to flag |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | AgentsNeedingSupportResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/agent-analytics/top-performers

**Summary**: Get top performers

**Tags**: Agent Analytics

Get leaderboard of top performing agents (admin only).

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| metric | query | string | no | Metric to rank by |
| limit | query | integer | no | Maximum results |
| period_days | query | integer | no | Analysis period in days |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | TopPerformersResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/agents

**Summary**: List agents

**Tags**: Agents

Get paginated list of agents with optional filters.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| page | query | integer | no | Page number |
| page_size | query | integer | no | Items per page |
| city | query | string \| null | no | Filter by service area city |
| specialty | query | string \| null | no | Filter by specialty |
| property_type | query | string \| null | no | Filter by property type |
| min_rating | query | number \| null | no | Minimum rating |
| agency_id | query | string \| null | no | Filter by agency ID |
| is_verified | query | boolean \| null | no | Filter by verified status |
| language | query | string \| null | no | Filter by language |
| sort_by | query | string | no | Sort by: rating, listings, reviews, created |
| sort_order | query | string | no | Sort order: asc or desc |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | AgentProfileListResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/agents/appointments

**Summary**: List appointments

**Tags**: Agents

Get viewing appointments for the authenticated agent.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| page | query | integer | no | Page number |
| page_size | query | integer | no | Items per page |
| status | query | string \| null | no | Filter by status |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | ViewingAppointmentListResponse |
| 422 | Validation Error | HTTPValidationError |

## PATCH /api/v1/agents/appointments/{appointment_id}

**Summary**: Update appointment

**Tags**: Agents

Update appointment status (agent only).

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| appointment_id | path | string | yes |  |
| access_token | cookie | string \| null | no |  |

**Request Body**

- Required: yes
- application/json: ViewingAppointmentUpdate

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | ViewingAppointmentResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/agents/inquiries

**Summary**: List inquiries

**Tags**: Agents

Get inquiries for the authenticated agent.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| page | query | integer | no | Page number |
| page_size | query | integer | no | Items per page |
| status | query | string \| null | no | Filter by status |
| inquiry_type | query | string \| null | no | Filter by inquiry type |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | AgentInquiryListResponse |
| 422 | Validation Error | HTTPValidationError |

## PATCH /api/v1/agents/inquiries/{inquiry_id}

**Summary**: Update inquiry

**Tags**: Agents

Update inquiry status (agent only).

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| inquiry_id | path | string | yes |  |
| access_token | cookie | string \| null | no |  |

**Request Body**

- Required: yes
- application/json: AgentInquiryUpdate

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | AgentInquiryResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/agents/profile

**Summary**: Get own profile

**Tags**: Agents

Get the authenticated agent's profile.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | AgentProfileResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/agents/profile

**Summary**: Create profile

**Tags**: Agents

Create an agent profile for the authenticated user.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| access_token | cookie | string \| null | no |  |

**Request Body**

- Required: yes
- application/json: AgentProfileCreate

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 201 | Successful Response | AgentProfileResponse |
| 422 | Validation Error | HTTPValidationError |

## PATCH /api/v1/agents/profile

**Summary**: Update profile

**Tags**: Agents

Update the authenticated agent's profile.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| access_token | cookie | string \| null | no |  |

**Request Body**

- Required: yes
- application/json: AgentProfileUpdate

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | AgentProfileResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/agents/{agent_id}

**Summary**: Get agent details

**Tags**: Agents

Get detailed agent profile by ID.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| agent_id | path | string | yes |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | AgentProfileResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/agents/{agent_id}/contact

**Summary**: Contact agent

**Tags**: Agents

Send an inquiry to an agent (contact form).

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| agent_id | path | string | yes |  |

**Request Body**

- Required: yes
- application/json: AgentInquiryCreate

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 201 | Successful Response | AgentInquiryResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/agents/{agent_id}/listings

**Summary**: Get agent listings

**Tags**: Agents

Get properties listed by an agent.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| agent_id | path | string | yes |  |
| listing_type | query | string \| null | no | Filter by listing type (sale/rent) |
| limit | query | integer | no | Max results |
| offset | query | integer | no | Offset for pagination |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | AgentListingListResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/agents/{agent_id}/schedule-viewing

**Summary**: Schedule viewing

**Tags**: Agents

Request a property viewing appointment with an agent.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| agent_id | path | string | yes |  |

**Request Body**

- Required: yes
- application/json: ViewingAppointmentCreate

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 201 | Successful Response | ViewingAppointmentResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/analytics/outbound

**Summary**: Record an outbound click

**Tags**: Analytics

Records a click that leaves the site: the target, the slot and the campaign.

**Request Body**

- Required: yes
- application/json: OutboundClickRequest

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 204 | Successful Response |  |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/anomalies

**Summary**: List Anomalies

**Tags**: Anomalies

List market anomalies with optional filters.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| severity | query | string \| null | no | Filter by severity |
| anomaly_type | query | string \| null | no | Filter by anomaly type |
| scope_type | query | string \| null | no | Filter by scope type |
| scope_id | query | string \| null | no | Filter by scope ID |
| limit | query | integer | no | Max results to return |
| offset | query | integer | no | Number of results to skip |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | AnomalyListResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/anomalies/stats

**Summary**: Get Anomaly Stats

**Tags**: Anomalies

Get anomaly statistics summary.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | AnomalyStatsResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/anomalies/stream

**Summary**: Stream Anomalies

**Tags**: Anomalies

Stream real-time anomaly updates via Server-Sent Events. This endpoint establishes a long-lived connection for pushing real-time anomaly detections to connected clients.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | object |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/anomalies/{anomaly_id}

**Summary**: Get Anomaly

**Tags**: Anomalies

Get a specific anomaly by ID.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| anomaly_id | path | string | yes |  |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | AnomalyResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/anomalies/{anomaly_id}/dismiss

**Summary**: Dismiss Anomaly

**Tags**: Anomalies

Dismiss an anomaly.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| anomaly_id | path | string | yes |  |
| access_token | cookie | string \| null | no |  |

**Request Body**

- Required: yes
- application/json: AnomalyDismissRequest

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | object |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/audit

**Summary**: List Audit Logs

**Tags**: Admin, Audit

Query audit log entries with filters and pagination.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| action | query | string \| null | no |  |
| actor_id | query | string \| null | no |  |
| resource | query | string \| null | no |  |
| request_id | query | string \| null | no |  |
| start_time | query | string \| null | no |  |
| end_time | query | string \| null | no |  |
| limit | query | integer | no |  |
| offset | query | integer | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | object |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/audit/verify

**Summary**: Verify Audit Chain

**Tags**: Admin, Audit

Verify hash-chain integrity of the audit log.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| limit | query | integer | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | object |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/audit/{entry_id}

**Summary**: Get Audit Entry

**Tags**: Admin, Audit

Get a single audit log entry by ID.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| entry_id | path | string | yes |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | object |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/auth/admin/unlock-account

**Summary**: Unlock a locked account

**Tags**: JWT Auth

Admin endpoint to unlock a user account that was locked due to failed login attempts.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| access_token | cookie | string \| null | no |  |

**Request Body**

- Required: yes
- application/json: object

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | MessageResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/auth/forgot-password

**Summary**: Request password reset

**Tags**: JWT Auth

Request a password reset email.

**Request Body**

- Required: yes
- application/json: object

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | MessageResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/auth/login

**Summary**: Login with email and password

**Tags**: JWT Auth

Authenticate user and return tokens.

**Request Body**

- Required: yes
- application/json: UserLogin

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | TokenResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/auth/logout

**Summary**: Logout user

**Tags**: JWT Auth

Invalidate the current session and clear cookies.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| refresh_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | MessageResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/auth/me

**Summary**: Get current user

**Tags**: JWT Auth

Get the currently authenticated user's profile.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | UserResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/auth/oauth/apple

**Summary**: Start Apple OAuth flow

**Tags**: JWT Auth

Redirect to Apple for Sign In.

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | object |

## GET /api/v1/auth/oauth/callback

**Summary**: OAuth callback

**Tags**: JWT Auth

Handle OAuth callback from providers.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| code | query | string \| null | no |  |
| state | query | string \| null | no |  |
| error | query | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | TokenResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/auth/oauth/google

**Summary**: Start Google OAuth flow

**Tags**: JWT Auth

Redirect to Google for OAuth authentication.

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | object |

## POST /api/v1/auth/refresh

**Summary**: Refresh access token

**Tags**: JWT Auth

Exchange refresh token for new access token.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| refresh_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | TokenResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/auth/register

**Summary**: Register a new user

**Tags**: JWT Auth

Create a new user account with email and password.

**Request Body**

- Required: yes
- application/json: UserCreate

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 201 | Successful Response | TokenResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/auth/request-code

**Summary**: Request Code

**Tags**: Auth

**Request Body**

- Required: yes
- application/json: RequestCodeBody

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | object |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/auth/resend-verification

**Summary**: Resend verification email

**Tags**: JWT Auth

Request a new email verification token.

**Request Body**

- Required: yes
- application/json: object

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | MessageResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/auth/reset-password

**Summary**: Reset password

**Tags**: JWT Auth

Reset password using token from email.

**Request Body**

- Required: yes
- application/json: object

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | MessageResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/auth/session

**Summary**: Get Session

**Tags**: Auth

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| X-Session-Token | header | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | SessionInfo |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/auth/verify-code

**Summary**: Verify Code

**Tags**: Auth

**Request Body**

- Required: yes
- application/json: VerifyCodeBody

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | SessionInfo |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/auth/verify-email

**Summary**: Verify email address

**Tags**: JWT Auth

Verify user email with token sent via email.

**Request Body**

- Required: yes
- application/json: object

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | MessageResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/bulk-jobs

**Summary**: List Bulk Jobs

**Tags**: Bulk Jobs

List bulk jobs with pagination and filtering. Supports filtering by: - job_type: import or export - status: pending, running, completed, failed, cancelled - source_type: url, file_upload, portal_api, search

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| page | query | integer | no |  |
| page_size | query | integer | no |  |
| job_type | query | string \| null | no |  |
| status | query | string \| null | no |  |
| source_type | query | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | BulkJobListResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/bulk-jobs/export

**Summary**: Create Export Job

**Tags**: Bulk Jobs

Start a new bulk export job. The export runs in the background using FastAPI BackgroundTasks. Use GET /bulk-jobs/{job_id} to check progress and get download URL.

**Request Body**

- Required: yes
- application/json: BulkExportRequest

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 201 | Successful Response | BulkJobCreateResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/bulk-jobs/import

**Summary**: Create Import Job

**Tags**: Bulk Jobs

Start a new bulk import job. The import runs in the background using FastAPI BackgroundTasks. Use GET /bulk-jobs/{job_id} to check progress.

**Request Body**

- Required: yes
- application/json: BulkImportRequest

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 201 | Successful Response | BulkJobCreateResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/bulk-jobs/{job_id}

**Summary**: Get Bulk Job

**Tags**: Bulk Jobs

Get details and status of a specific bulk job.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| job_id | path | string | yes |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | BulkJobResponse |
| 422 | Validation Error | HTTPValidationError |

## DELETE /api/v1/bulk-jobs/{job_id}

**Summary**: Delete Bulk Job

**Tags**: Bulk Jobs

Delete a bulk job record. Only completed, failed, or cancelled jobs can be deleted.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| job_id | path | string | yes |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 204 | Successful Response |  |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/bulk-jobs/{job_id}/cancel

**Summary**: Cancel Bulk Job

**Tags**: Bulk Jobs

Cancel a running bulk job. Only jobs in 'pending' or 'running' status can be cancelled.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| job_id | path | string | yes |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | BulkJobResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/capabilities

**Summary**: What this deployment can actually do

**Tags**: Capabilities

Reports the enabled authentication providers, whether e-mail is really sent, and whether error tracking is configured. The frontend uses it to hide features the deployment cannot serve.

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | object |

## GET /api/v1/catalogue/stats

**Summary**: What the catalogue holds

**Tags**: Catalogue

The live numbers of the catalogue: the properties, the cities they are in, the agents and the currencies. An empty catalogue answers with zeros rather than an error.

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | CatalogueStatsResponse |

## POST /api/v1/chat

**Summary**: Chat Endpoint

**Tags**: Chat, Chat

Process a chat message using the hybrid agent with session persistence. Requires API key authentication.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| X-User-Email | header | string \| null | no |  |

**Request Body**

- Required: yes
- application/json: ChatRequest

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | ChatResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/chat/free

**Summary**: Chat Free Endpoint

**Tags**: Chat (Free Tier), Chat

Free tier chat — no API key required. Uses the free LLM provider cascade (OpenRouter free → Google Flash → Ollama) with hourly/daily rate limits per client IP.

**Request Body**

- Required: yes
- application/json: ChatRequest

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | ChatResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/cma

**Summary**: List Cma Reports

**Tags**: CMA, CMA

List user's CMA reports. Supports pagination and filtering by status.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| status | query | string \| null | no |  |
| page | query | integer | no |  |
| page_size | query | integer | no |  |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | CMAReportListResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/cma/comparables/{property_id}

**Summary**: Find Comparables

**Tags**: CMA, CMA

Find comparable properties for a subject property. Uses multi-factor scoring (location, type, size, rooms, recency, amenities) to identify the most similar properties. Returns list of comparable properties with similarity scores.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| property_id | path | string | yes |  |
| max_distance_km | query | number | no |  |
| min_score | query | number | no |  |
| max_results | query | integer | no |  |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | array[CMAComparableResponse] |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/cma/generate

**Summary**: Generate Cma Report

**Tags**: CMA, CMA

Generate a Comparative Market Analysis (CMA) report. This endpoint: 1. Fetches the subject property 2. Finds comparable properties using multi-factor scoring 3. Calculates adjustments for differences 4. Produces a final valuation estimate The report is saved and can be retrieved later or exported as PDF.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| access_token | cookie | string \| null | no |  |

**Request Body**

- Required: yes
- application/json: CMAReportCreate

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | CMAReportResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/cma/{report_id}

**Summary**: Get Cma Report

**Tags**: CMA, CMA

Retrieve a saved CMA report by ID. Only the report owner can access the report.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| report_id | path | string | yes |  |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | CMAReportResponse |
| 422 | Validation Error | HTTPValidationError |

## DELETE /api/v1/cma/{report_id}

**Summary**: Delete Cma Report

**Tags**: CMA, CMA

Delete a CMA report. Only the report owner can delete the report.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| report_id | path | string | yes |  |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 204 | Successful Response |  |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/cma/{report_id}/pdf

**Summary**: Download Cma Pdf

**Tags**: CMA, CMA

Download CMA report as PDF. Generates a professional PDF report with: - Executive summary - Subject property details - Comparables grid - Adjustments breakdown - Final valuation

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| report_id | path | string | yes |  |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | object |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/collections

**Summary**: List user's collections

**Tags**: Collections

Get all collections for the current authenticated user.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | CollectionListResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/collections

**Summary**: Create a collection

**Tags**: Collections

Create a new collection to organize favorited properties.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| access_token | cookie | string \| null | no |  |

**Request Body**

- Required: yes
- application/json: CollectionCreate

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 201 | Successful Response | CollectionResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/collections/default

**Summary**: Get or create default collection

**Tags**: Collections

Get the user's default collection, creating one if it doesn't exist.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | CollectionResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/collections/{collection_id}

**Summary**: Get a collection

**Tags**: Collections

Get a specific collection by ID.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| collection_id | path | string | yes |  |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | CollectionResponse |
| 422 | Validation Error | HTTPValidationError |

## PUT /api/v1/collections/{collection_id}

**Summary**: Update a collection

**Tags**: Collections

Update a collection's name or description.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| collection_id | path | string | yes |  |
| access_token | cookie | string \| null | no |  |

**Request Body**

- Required: yes
- application/json: CollectionUpdate

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | CollectionResponse |
| 422 | Validation Error | HTTPValidationError |

## DELETE /api/v1/collections/{collection_id}

**Summary**: Delete a collection

**Tags**: Collections

Delete a collection. Favorites will become uncategorized.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| collection_id | path | string | yes |  |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 204 | Successful Response |  |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/data-sources

**Summary**: List Data Sources

**Tags**: Data Sources

List all data sources with pagination and filtering.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| page | query | integer | no |  |
| page_size | query | integer | no |  |
| status | query | string \| null | no |  |
| source_type | query | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | DataSourceListResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/data-sources

**Summary**: Create Data Source

**Tags**: Data Sources

Create a new data source configuration.

**Request Body**

- Required: yes
- application/json: DataSourceCreate

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 201 | Successful Response | DataSourceResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/data-sources/test

**Summary**: Test Data Source

**Tags**: Data Sources

Test a data source connection without saving.

**Request Body**

- Required: yes
- application/json: DataSourceTestRequest

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | DataSourceTestResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/data-sources/{source_id}

**Summary**: Get Data Source

**Tags**: Data Sources

Get a specific data source by ID.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| source_id | path | string | yes |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | DataSourceResponse |
| 422 | Validation Error | HTTPValidationError |

## PATCH /api/v1/data-sources/{source_id}

**Summary**: Update Data Source

**Tags**: Data Sources

Update a data source configuration.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| source_id | path | string | yes |  |

**Request Body**

- Required: yes
- application/json: DataSourceUpdate

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | DataSourceResponse |
| 422 | Validation Error | HTTPValidationError |

## DELETE /api/v1/data-sources/{source_id}

**Summary**: Delete Data Source

**Tags**: Data Sources

Delete a data source. Requires confirm=true to prevent accidental deletion.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| source_id | path | string | yes |  |
| confirm | query | boolean | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 204 | Successful Response |  |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/data-sources/{source_id}/history

**Summary**: Get Sync History

**Tags**: Data Sources

Get sync history for a data source.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| source_id | path | string | yes |  |
| page | query | integer | no |  |
| page_size | query | integer | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | SyncHistoryResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/data-sources/{source_id}/sync

**Summary**: Sync Data Source

**Tags**: Data Sources

Trigger a manual sync for a data source.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| source_id | path | string | yes |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | DataSourceSyncResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/documents

**Summary**: List documents

**Tags**: Documents

List all documents for the current user with optional filters.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| property_id | query | string \| null | no | Filter by property ID |
| category | query | string \| null | no | Filter by category |
| ocr_status | query | string \| null | no | Filter by OCR status |
| search_query | query | string \| null | no | Search in filename/description |
| sort_by | query | string | no | Sort field |
| sort_order | query | string | no | Sort order (asc/desc) |
| page | query | integer | no | Page number |
| page_size | query | integer | no | Items per page |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | DocumentListResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/documents

**Summary**: Upload a document

**Tags**: Documents

Upload a document file with optional metadata. Supports PDF, DOC, DOCX, JPG, PNG. Max size: 10MB.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| access_token | cookie | string \| null | no |  |

**Request Body**

- Required: yes
- multipart/form-data: Body_upload_document_api_v1_documents_post

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 201 | Successful Response | DocumentUploadResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/documents/expiring

**Summary**: Get expiring documents

**Tags**: Documents

Get documents that will expire within the specified number of days.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| days_ahead | query | integer | no | Days ahead to check |
| limit | query | integer | no |  |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | ExpiringDocumentsResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/documents/{document_id}

**Summary**: Download a document

**Tags**: Documents

Download a previously uploaded document.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| document_id | path | string | yes |  |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Document file | object |
| 422 | Validation Error | HTTPValidationError |

## PATCH /api/v1/documents/{document_id}

**Summary**: Update document metadata

**Tags**: Documents

Update document category, tags, description, or expiry date.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| document_id | path | string | yes |  |
| access_token | cookie | string \| null | no |  |

**Request Body**

- Required: yes
- application/json: DocumentUpdate

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | DocumentResponse |
| 422 | Validation Error | HTTPValidationError |

## DELETE /api/v1/documents/{document_id}

**Summary**: Delete a document

**Tags**: Documents

Delete a document and its associated file.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| document_id | path | string | yes |  |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 204 | Successful Response |  |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/export/properties

**Summary**: Export Properties

**Tags**: Export, Export

**Request Body**

- Required: yes
- application/json: ExportPropertiesRequest

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | object |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/favorites

**Summary**: List user's favorites

**Tags**: Favorites

Get all favorited properties for the current user with full property data.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| collection_id | query | string \| null | no | Filter by collection |
| limit | query | integer | no |  |
| offset | query | integer | no |  |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | FavoriteListResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/favorites

**Summary**: Add a property to favorites

**Tags**: Favorites

Add a property to the user's favorites.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| access_token | cookie | string \| null | no |  |

**Request Body**

- Required: yes
- application/json: FavoriteCreate

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 201 | Successful Response | FavoriteResponse |
| 422 | Validation Error | HTTPValidationError |

## DELETE /api/v1/favorites/by-property/{property_id}

**Summary**: Remove favorite by property ID

**Tags**: Favorites

Remove a property from favorites by property ID.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| property_id | path | string | yes |  |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 204 | Successful Response |  |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/favorites/check/{property_id}

**Summary**: Check if property is favorited

**Tags**: Favorites

Quick check if a property is in the user's favorites.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| property_id | path | string | yes |  |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | FavoriteCheckResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/favorites/ids

**Summary**: Get all favorited property IDs

**Tags**: Favorites

Get a list of all property IDs favorited by the user. Useful for UI heart icons.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | array[string] |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/favorites/{favorite_id}

**Summary**: Get a favorite with property data

**Tags**: Favorites

Get a specific favorite by ID with full property data.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| favorite_id | path | string | yes |  |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | FavoriteWithPropertyResponse |
| 422 | Validation Error | HTTPValidationError |

## PATCH /api/v1/favorites/{favorite_id}

**Summary**: Update a favorite

**Tags**: Favorites

Update a favorite's notes or move to a different collection.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| favorite_id | path | string | yes |  |
| access_token | cookie | string \| null | no |  |

**Request Body**

- Required: yes
- application/json: FavoriteUpdate

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | FavoriteResponse |
| 422 | Validation Error | HTTPValidationError |

## DELETE /api/v1/favorites/{favorite_id}

**Summary**: Remove a favorite

**Tags**: Favorites

Remove a property from favorites.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| favorite_id | path | string | yes |  |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 204 | Successful Response |  |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/favorites/{favorite_id}/move/{collection_id}

**Summary**: Move favorite to collection

**Tags**: Favorites

Move a favorite to a different collection.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| favorite_id | path | string | yes |  |
| collection_id | path | string | yes |  |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | FavoriteResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/feedback/metrics/relevance

**Summary**: Get aggregated relevance metrics

**Tags**: Feedback, Admin

Return aggregated search relevance metrics for admin monitoring. Measures user-rated match accuracy against the ≥80% target.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| since | query | string \| null | no | ISO date to filter ratings from |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | RelevanceMetrics |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/feedback/rating

**Summary**: Submit a relevance rating for a search result

**Tags**: Feedback

Submit a thumbs-up/down rating for a search result. Ratings are stored anonymously — no user authentication required.

**Request Body**

- Required: yes
- application/json: FeedbackCreate

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 201 | Successful Response | FeedbackResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/filter-presets

**Summary**: List user's filter presets

**Tags**: Filter Presets

Get all filter presets for the current authenticated user.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| limit | query | integer | no | Maximum presets to return |
| offset | query | integer | no | Offset for pagination |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | FilterPresetListResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/filter-presets

**Summary**: Create a filter preset

**Tags**: Filter Presets

Create a new filter preset for quick access to common searches.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| access_token | cookie | string \| null | no |  |

**Request Body**

- Required: yes
- application/json: FilterPresetCreate

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 201 | Successful Response | FilterPresetResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/filter-presets/default

**Summary**: Get user's default preset

**Tags**: Filter Presets

Get the default filter preset for the current user.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | FilterPresetResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/filter-presets/{preset_id}

**Summary**: Get a filter preset

**Tags**: Filter Presets

Get a specific filter preset by ID.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| preset_id | path | string | yes |  |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | FilterPresetResponse |
| 422 | Validation Error | HTTPValidationError |

## PATCH /api/v1/filter-presets/{preset_id}

**Summary**: Update a filter preset

**Tags**: Filter Presets

Update a filter preset's name, description, or filters.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| preset_id | path | string | yes |  |
| access_token | cookie | string \| null | no |  |

**Request Body**

- Required: yes
- application/json: FilterPresetUpdate

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | FilterPresetResponse |
| 422 | Validation Error | HTTPValidationError |

## DELETE /api/v1/filter-presets/{preset_id}

**Summary**: Delete a filter preset

**Tags**: Filter Presets

Permanently delete a filter preset.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| preset_id | path | string | yes |  |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 204 | Successful Response |  |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/filter-presets/{preset_id}/set-default

**Summary**: Set preset as default

**Tags**: Filter Presets

Set this preset as the default for the user.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| preset_id | path | string | yes |  |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | FilterPresetResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/filter-presets/{preset_id}/use

**Summary**: Mark preset as used

**Tags**: Filter Presets

Increment usage count when user applies a filter preset.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| preset_id | path | string | yes |  |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | FilterPresetResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/investment/analyze

**Summary**: Analyze Investment

**Tags**: Investment, Investment

Calculate investment property metrics. Returns comprehensive investment analysis including: - Cash on Cash ROI - Capitalization Rate (Cap Rate) - Gross and Net Rental Yield - Monthly and Annual Cash Flow - Investment Score (0-100) This endpoint returns JSON only. For downloadable reports, use the `/investment/report` endpoint.

**Request Body**

- Required: yes
- application/json: InvestmentReportRequest

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | InvestmentAnalysisResult |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/investment/analyze/advanced

**Summary**: Analyze Investment Advanced

**Tags**: Investment, Investment

Advanced investment analysis with multi-year projections. Provides: - Multi-year cash flow projections - Tax implications (depreciation, deductions) - Appreciation scenarios (pessimistic, realistic, optimistic) - Risk assessment scoring This is the same as the `/tools/advanced-investment-analysis` endpoint but grouped under the investment router for better organization.

**Request Body**

- Required: yes
- application/json: AdvancedInvestmentInput

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | AdvancedInvestmentResult |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/investment/report

**Summary**: Generate Investment Report

**Tags**: Investment, Investment

Generate downloadable investment analysis report. Provides comprehensive investment analysis including: - Key metrics (ROI, cap rate, cash flow, rental yield) - Monthly/annual breakdown of income and expenses - Investment score with category breakdown - Optional multi-year projection with cash flow forecasts **Report Formats:** - **PDF**: Professional formatted document with tables and visualizations - **Markdown**: Plain text report for easy viewing and archiving - **JSON**: Structured data for programmatic access **Example Request:** ```json { "property_price": 350000, "monthly_rent": 2800, "down_payment_percent": 20, "interest_rate": 4.5, "loan_years": 30, "property_tax_monthly": 350, "insurance_monthly": 150, "include_projection": true, "projection_years": 10 } ```

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| format | query | ReportFormat | no | Report format (pdf, md, or json) |

**Request Body**

- Required: yes
- application/json: InvestmentReportRequest

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Investment report generated successfully | object |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/leads

**Summary**: List leads

**Tags**: Lead Scoring

Get paginated list of leads. Agents see their assigned leads, admins see all.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| page | query | integer | no | Page number |
| page_size | query | integer | no | Items per page |
| status | query | string \| null | no | Filter by status |
| score_min | query | integer \| null | no | Minimum score |
| score_max | query | integer \| null | no | Maximum score |
| source | query | string \| null | no | Filter by source |
| has_email | query | boolean \| null | no | Filter by has email |
| sort_by | query | string | no | Sort field |
| sort_order | query | string | no | Sort order (asc/desc) |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | LeadListResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/leads

**Summary**: Create and score a lead

**Tags**: Lead Scoring

Create a new lead and immediately calculate its priority score based on budget fit, urgency, and engagement signals.

**Request Body**

- Required: yes
- application/json: CreateAndScoreLeadRequest

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 201 | Successful Response | LeadWithScoreResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/leads/bulk/assign

**Summary**: Bulk assign leads

**Tags**: Lead Scoring

Assign multiple leads to an agent. Admin only.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| access_token | cookie | string \| null | no |  |

**Request Body**

- Required: yes
- application/json: BulkAssignRequest

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | BulkOperationResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/leads/bulk/status

**Summary**: Bulk update status

**Tags**: Lead Scoring

Update status for multiple leads.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| access_token | cookie | string \| null | no |  |

**Request Body**

- Required: yes
- application/json: BulkStatusUpdateRequest

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | BulkOperationResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/leads/export

**Summary**: Export leads

**Tags**: Lead Scoring

Export leads to CSV. Admin only.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| status | query | string \| null | no | Filter by status |
| score_min | query | integer \| null | no | Minimum score |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | object |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/leads/funnel

**Summary**: Get agent lead funnel

**Tags**: Lead Scoring

Get lead funnel statistics for the current agent or a specified agent. Shows leads by priority tier and status for visualization.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| agent_id | query | string \| null | no | Agent ID (admin only, defaults to current user) |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | AgentFunnelResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/leads/high-value

**Summary**: Get high-value leads

**Tags**: Lead Scoring

Get leads with scores above threshold (70+).

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| threshold | query | integer | no | Score threshold |
| limit | query | integer | no | Maximum results |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | array[LeadWithScoreResponse] |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/leads/scores

**Summary**: Score lead data

**Tags**: Lead Scoring

Calculate priority score for provided lead data without creating a record. Returns budget fit, urgency, and engagement breakdown.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| access_token | cookie | string \| null | no |  |

**Request Body**

- Required: yes
- application/json: LeadScoreInputSchema

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | PrioritizedScoreResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/leads/scores/recalculate

**Summary**: Recalculate lead scores

**Tags**: Lead Scoring

Trigger recalculation of lead scores. Admin only.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| access_token | cookie | string \| null | no |  |

**Request Body**

- Required: no
- application/json: RecalculateScoresRequest | null

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | RecalculateScoresResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/leads/scores/statistics

**Summary**: Get scoring statistics

**Tags**: Lead Scoring

Get overall lead scoring statistics.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | object |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/leads/track

**Summary**: Track visitor interaction

**Tags**: Lead Scoring

Record a visitor interaction for lead scoring. Uses visitor_id cookie.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| access_token | cookie | string \| null | no |  |

**Request Body**

- Required: yes
- application/json: TrackInteractionRequest

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 204 | Successful Response |  |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/leads/visitor

**Summary**: Create or get visitor

**Tags**: Lead Scoring

Create a new visitor record or get existing one by visitor_id.

**Request Body**

- Required: yes
- application/json: LeadCreate

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 201 | Successful Response | LeadResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/leads/{lead_id}

**Summary**: Get lead details

**Tags**: Lead Scoring

Get detailed lead information including interactions and score history.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| lead_id | path | string | yes |  |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | LeadDetailResponse |
| 422 | Validation Error | HTTPValidationError |

## PATCH /api/v1/leads/{lead_id}

**Summary**: Update lead

**Tags**: Lead Scoring

Update lead information.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| lead_id | path | string | yes |  |
| access_token | cookie | string \| null | no |  |

**Request Body**

- Required: yes
- application/json: LeadUpdate

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | LeadResponse |
| 422 | Validation Error | HTTPValidationError |

## DELETE /api/v1/leads/{lead_id}

**Summary**: Delete lead data

**Tags**: Lead Scoring

Delete all lead data (GDPR right to be forgotten).

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| lead_id | path | string | yes |  |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | MessageResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/leads/{lead_id}/assign

**Summary**: Assign agent to lead

**Tags**: Lead Scoring

Assign an agent to a lead. Admin only.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| lead_id | path | string | yes |  |
| access_token | cookie | string \| null | no |  |

**Request Body**

- Required: yes
- application/json: AgentAssignmentCreate

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 201 | Successful Response | AgentAssignmentResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/leads/{lead_id}/score

**Summary**: Get lead score breakdown

**Tags**: Lead Scoring

Get detailed score breakdown with factors and recommendations.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| lead_id | path | string | yes |  |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | LeadScoreBreakdown |
| 422 | Validation Error | HTTPValidationError |

## PATCH /api/v1/leads/{lead_id}/status

**Summary**: Update lead status

**Tags**: Lead Scoring

Update lead status (new, contacted, qualified, converted, lost).

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| lead_id | path | string | yes |  |
| status | query | string | yes | New status |
| notes | query | string \| null | no | Status change notes |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | LeadResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/market/area/{city}

**Summary**: Get insights for a single area

**Tags**: Market Analytics

Get detailed market insights for a specific city/area.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| city | path | string | yes |  |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | AreaInsightsResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/market/compare

**Summary**: Compare two areas

**Tags**: Market Analytics

Compare market metrics between two cities/areas side by side.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| city1 | query | string | yes | First city to compare |
| city2 | query | string | yes | Second city to compare |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | AreaComparisonResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/market/indicators

**Summary**: Get market indicators

**Tags**: Market Analytics

Get current market health indicators (rising/falling/stable).

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| city | query | string \| null | no | Filter by city |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | MarketIndicatorsResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/market/price-history/{property_id}

**Summary**: Get price history for a property

**Tags**: Market Analytics

Get historical price snapshots for a specific property.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| property_id | path | string | yes |  |
| limit | query | integer | no | Maximum snapshots to return |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | PriceHistoryResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/market/trends

**Summary**: Get market trend data

**Tags**: Market Analytics

Get average prices by city/district over time.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| city | query | string \| null | no | Filter by city |
| district | query | string \| null | no | Filter by district |
| interval | query | string | no | Interval: month, quarter, year |
| months_back | query | integer | no | Months of history |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | MarketTrendsResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/mcp/allowlist

**Summary**: Get Allowlist

**Tags**: MCP Admin

Get current MCP connector allowlist configuration. Returns the full allowlist including: - Current edition - Allowlisted connectors (CE accessible) - Restricted connectors (PRO/Enterprise only)

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | MCPAllowlistResponse |

## POST /api/v1/mcp/allowlist

**Summary**: Add To Allowlist

**Tags**: MCP Admin

Add a connector to the allowlist at runtime. Note: This modifies the in-memory config only. For persistence, update the YAML file directly.

**Request Body**

- Required: yes
- application/json: MCPAllowlistAddRequest

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 201 | Successful Response | MCPAllowlistEntryResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/mcp/allowlist/reload

**Summary**: Reload Allowlist

**Tags**: MCP Admin

Reload allowlist configuration from YAML file. Use this after updating the YAML file to apply changes without restarting the application.

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | MCPReloadResponse |

## GET /api/v1/mcp/allowlist/violations

**Summary**: Get Violations

**Tags**: MCP Admin

Get all logged allowlist violations for audit. Returns violation records including: - Timestamp - Connector name - Operation attempted - Context and edition info

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | MCPViolationsListResponse |

## DELETE /api/v1/mcp/allowlist/violations

**Summary**: Clear Violations

**Tags**: MCP Admin

Clear all logged allowlist violations. Use with caution - this removes audit trail.

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 204 | Successful Response |  |

## DELETE /api/v1/mcp/allowlist/{name}

**Summary**: Remove From Allowlist

**Tags**: MCP Admin

Remove a connector from the allowlist. Note: This modifies the in-memory config only. For persistence, update the YAML file directly.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| name | path | string | yes |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 204 | Successful Response |  |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/mcp/connectors

**Summary**: List Connectors

**Tags**: MCP Admin

List all connectors with status. Returns all registered connectors with their current status: - **active**: Connector is connected and healthy - **disabled**: Connector is configured but not enabled - **error**: Connector has connection/health issues - **not_instantiated**: Connector registered but no instance Combines information from: - Allowlist config (YAML) - Registry (registered connectors)

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | MCPConnectorsListResponse |

## GET /api/v1/mcp/connectors/{name}

**Summary**: Get Connector Details

**Tags**: MCP Admin

Get detailed information about a specific connector. Returns comprehensive connector information including: - Basic info (name, description, status) - Configuration details (sanitized) - Rate limit settings - Instance status if available

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| name | path | string | yes |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Connector details | MCPConnectorDetailResponse |
| 404 | Connector not found |  |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/mcp/connectors/{name}/health

**Summary**: Health Check Connector

**Tags**: MCP Admin

Perform health check on a specific connector. Returns health status including: - Success/failure status - Response time in milliseconds - Any errors or warnings - Detailed health information

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| name | path | string | yes |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Health check completed | MCPConnectorHealthResponse |
| 404 | Connector not found |  |
| 422 | Validation Error | HTTPValidationError |
| 503 | Connector unhealthy |  |

## GET /api/v1/mcp/health

**Summary**: Health Check

**Tags**: MCP Admin

Health check for MCP connector system. Returns: - Overall status (healthy/degraded/unhealthy) - Health check results for each instantiated connector

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | MCPHealthResponse |

## GET /api/v1/model-preferences

**Summary**: List user model preferences

**Tags**: Model Preferences

Get all model preferences for the current user.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | TaskModelPreferenceListResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/model-preferences

**Summary**: Create model preference

**Tags**: Model Preferences

Create a new model preference for a task type.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| access_token | cookie | string \| null | no |  |

**Request Body**

- Required: yes
- application/json: TaskModelPreferenceCreate

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 201 | Successful Response | TaskModelPreferenceResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/model-preferences/system/cost-estimate

**Summary**: Get cost estimate for model

**Tags**: Model Preferences

Get estimated cost for using a specific model.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| provider | query | string | yes | Provider name |
| model_name | query | string | yes | Model identifier |
| estimated_tokens | query | integer | no | Estimated tokens per request |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | ModelCostEstimate |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/model-preferences/system/defaults

**Summary**: Get system default preferences

**Tags**: Model Preferences

Get system default model preferences for all task types.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | SystemDefaultsResponse |
| 422 | Validation Error | HTTPValidationError |

## PUT /api/v1/model-preferences/{preference_id}

**Summary**: Update model preference

**Tags**: Model Preferences

Update an existing model preference.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| preference_id | path | string | yes |  |
| access_token | cookie | string \| null | no |  |

**Request Body**

- Required: yes
- application/json: TaskModelPreferenceUpdate

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | TaskModelPreferenceResponse |
| 422 | Validation Error | HTTPValidationError |

## DELETE /api/v1/model-preferences/{preference_id}

**Summary**: Delete model preference

**Tags**: Model Preferences

Delete a model preference. Will use system default after deletion.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| preference_id | path | string | yes |  |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 204 | Successful Response |  |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/model-preferences/{task_type}

**Summary**: Get preference for task type

**Tags**: Model Preferences

Get model preference for a specific task type (chat, search, tools, analysis, embedding).

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| task_type | path | string | yes |  |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | TaskModelPreferenceResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/profile

**Summary**: Get Profile

**Tags**: Profile

Get current user's profile.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | ProfileResponse |
| 422 | Validation Error | HTTPValidationError |

## PUT /api/v1/profile

**Summary**: Update Profile

**Tags**: Profile

Update current user's profile (partial update).

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| access_token | cookie | string \| null | no |  |

**Request Body**

- Required: yes
- application/json: ProfileUpdate

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | ProfileResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/profile/avatar

**Summary**: Upload Avatar

**Tags**: Profile

Upload avatar image.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| access_token | cookie | string \| null | no |  |

**Request Body**

- Required: yes
- multipart/form-data: Body_upload_avatar_api_v1_profile_avatar_post

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | AvatarUploadResponse |
| 422 | Validation Error | HTTPValidationError |

## DELETE /api/v1/profile/avatar

**Summary**: Delete Avatar

**Tags**: Profile

Delete user's avatar.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | object |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/profile/export

**Summary**: Request Data Export

**Tags**: Profile

Request GDPR data export (async processing).

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| access_token | cookie | string \| null | no |  |

**Request Body**

- Required: yes
- application/json: DataExportRequest

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | DataExportResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/profile/export/{export_id}

**Summary**: Get Export Status

**Tags**: Profile

Get data export job status.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| export_id | path | string | yes |  |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | DataExportStatusResponse |
| 422 | Validation Error | HTTPValidationError |

## PUT /api/v1/profile/privacy

**Summary**: Update Privacy Settings

**Tags**: Profile

Update privacy settings.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| access_token | cookie | string \| null | no |  |

**Request Body**

- Required: yes
- application/json: PrivacySettings

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | ProfileResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/prompt-templates

**Summary**: List Prompt Templates

**Tags**: Prompt Templates, Prompt Templates

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | array[PromptTemplateInfo] |

## POST /api/v1/prompt-templates/apply

**Summary**: Apply Prompt Template

**Tags**: Prompt Templates, Prompt Templates

**Request Body**

- Required: yes
- application/json: PromptTemplateApplyRequest

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | PromptTemplateApplyResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/push/subscribe

**Summary**: Subscribe To Push

**Tags**: Push Notifications

Register a push subscription for the current user. Args: body: Push subscription data from the browser user: Current authenticated user db: Database session device_name: Optional friendly name for the device Returns: Created subscription details Raises: HTTPException 409: If endpoint already registered to another user

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| device_name | query | string \| null | no |  |
| access_token | cookie | string \| null | no |  |

**Request Body**

- Required: yes
- application/json: PushSubscriptionCreate

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 201 | Successful Response | PushSubscriptionResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/push/subscriptions

**Summary**: List Push Subscriptions

**Tags**: Push Notifications

List all push subscriptions for the current user. Args: user: Current authenticated user db: Database session include_inactive: Whether to include inactive subscriptions Returns: List of subscriptions

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| include_inactive | query | boolean | no |  |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | PushSubscriptionListResponse |
| 422 | Validation Error | HTTPValidationError |

## DELETE /api/v1/push/subscriptions/{subscription_id}

**Summary**: Delete Push Subscription

**Tags**: Push Notifications

Delete a specific push subscription by ID. Args: subscription_id: ID of the subscription to delete user: Current authenticated user db: Database session Raises: HTTPException 404: If subscription not found or not owned by user

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| subscription_id | path | string | yes |  |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 204 | Successful Response |  |
| 422 | Validation Error | HTTPValidationError |

## DELETE /api/v1/push/unsubscribe

**Summary**: Unsubscribe From Push

**Tags**: Push Notifications

Remove a push subscription. Args: endpoint: The push subscription endpoint URL to unsubscribe user: Current authenticated user db: Database session

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| endpoint | query | string | yes |  |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 204 | Successful Response |  |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/push/vapid-public-key

**Summary**: Get Vapid Public Key

**Tags**: Push Notifications

Get VAPID public key for browser push subscription. This endpoint is public (no auth required) as the key is needed before the user can subscribe to push notifications. Returns: VAPID public key (base64url encoded) and enabled status

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | VapidPublicKeyResponse |

## POST /api/v1/rag/qa

**Summary**: Rag Qa

**Tags**: RAG, RAG

Simple QA over uploaded knowledge with citations. If LLM is unavailable, returns concatenated context as answer. Supports SSE streaming when stream=true.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| question | query | string \| null | no |  |
| top_k | query | integer | no |  |
| provider | query | string \| null | no |  |
| model | query | string \| null | no |  |
| X-User-Email | header | string \| null | no |  |

**Request Body**

- Required: no
- application/json: RagQaRequest | null

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | RagQaResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/rag/reset

**Summary**: Reset Rag Knowledge

**Tags**: RAG, RAG

Clear all indexed knowledge documents for local RAG (CE-safe).

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | RagResetResponse |

## POST /api/v1/rag/upload

**Summary**: Upload Documents

**Tags**: RAG, RAG

Upload documents and index for local RAG (CE-safe). PDF/DOCX require optional dependencies; unsupported types return a 422 when nothing is indexed.

**Request Body**

- Required: yes
- multipart/form-data: Body_upload_documents_api_v1_rag_upload_post

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | object |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/ranking/configs

**Summary**: List Configs

**Tags**: Ranking Configuration

List all ranking configurations. Requires API key authentication.

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | array[RankingConfigResponse] |

## POST /api/v1/ranking/configs

**Summary**: Create Config

**Tags**: Ranking Configuration

Create a new ranking configuration. Requires API key authentication.

**Request Body**

- Required: yes
- application/json: RankingConfigCreate

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 201 | Successful Response | RankingConfigResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/ranking/configs/active

**Summary**: Get Active Config

**Tags**: Ranking Configuration

Get the currently active ranking configuration. Returns the configuration marked as active, or the default if none active.

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | RankingConfigResponse |

## GET /api/v1/ranking/configs/weights

**Summary**: Get Active Weights

**Tags**: Ranking Configuration

Get the active ranking weights. This is a lightweight endpoint for internal use that returns just the weight values without full configuration details.

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | RankingWeightsResponse |

## GET /api/v1/ranking/configs/{config_id}

**Summary**: Get Config

**Tags**: Ranking Configuration

Get a specific ranking configuration by ID.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| config_id | path | string | yes |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | RankingConfigResponse |
| 422 | Validation Error | HTTPValidationError |

## PATCH /api/v1/ranking/configs/{config_id}

**Summary**: Update Config

**Tags**: Ranking Configuration

Update a ranking configuration. Only provided fields will be updated. Requires API key authentication.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| config_id | path | string | yes |  |

**Request Body**

- Required: yes
- application/json: RankingConfigUpdate

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | RankingConfigResponse |
| 422 | Validation Error | HTTPValidationError |

## DELETE /api/v1/ranking/configs/{config_id}

**Summary**: Delete Config

**Tags**: Ranking Configuration

Delete a ranking configuration. Cannot delete the active or default configuration. Requires API key authentication.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| config_id | path | string | yes |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 204 | Successful Response |  |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/ranking/configs/{config_id}/activate

**Summary**: Activate Config

**Tags**: Ranking Configuration

Activate a ranking configuration. This will deactivate any currently active configuration. Requires API key authentication.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| config_id | path | string | yes |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | RankingConfigResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/saved-searches

**Summary**: List user's saved searches

**Tags**: Saved Searches

Get all saved searches for the current authenticated user.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| include_inactive | query | boolean | no | Include paused/disabled searches |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | SavedSearchListResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/saved-searches

**Summary**: Create a saved search

**Tags**: Saved Searches

Save a search with filters and alert settings.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| access_token | cookie | string \| null | no |  |

**Request Body**

- Required: yes
- application/json: SavedSearchCreate

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 201 | Successful Response | SavedSearchResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/saved-searches/{search_id}

**Summary**: Get a saved search

**Tags**: Saved Searches

Get a specific saved search by ID.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| search_id | path | string | yes |  |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | SavedSearchResponse |
| 422 | Validation Error | HTTPValidationError |

## PATCH /api/v1/saved-searches/{search_id}

**Summary**: Update a saved search

**Tags**: Saved Searches

Update a saved search's name, filters, or alert settings.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| search_id | path | string | yes |  |
| access_token | cookie | string \| null | no |  |

**Request Body**

- Required: yes
- application/json: SavedSearchUpdate

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | SavedSearchResponse |
| 422 | Validation Error | HTTPValidationError |

## DELETE /api/v1/saved-searches/{search_id}

**Summary**: Delete a saved search

**Tags**: Saved Searches

Permanently delete a saved search.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| search_id | path | string | yes |  |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 204 | Successful Response |  |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/saved-searches/{search_id}/toggle-alert

**Summary**: Toggle alert for a saved search

**Tags**: Saved Searches

Enable or disable alerts for a saved search.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| search_id | path | string | yes |  |
| enabled | query | boolean | no | Enable or disable |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | SavedSearchResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/saved-searches/{search_id}/use

**Summary**: Mark search as used

**Tags**: Saved Searches

Increment usage count when user applies a saved search.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| search_id | path | string | yes |  |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | SavedSearchResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/search

**Summary**: Search Properties

**Tags**: Search, Search

Search for properties using semantic search and metadata filters. Results are cached for 5 minutes (TTL 300s).

**Request Body**

- Required: yes
- application/json: SearchRequest

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | SearchResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/settings/demo

**Summary**: Get Demo Mode

**Tags**: Settings

Get current demo mode preference.

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | object |

## POST /api/v1/settings/demo

**Summary**: Set Demo Mode

**Tags**: Settings

Set demo mode preference (stored in session for demo purposes). This endpoint allows toggling demo mode at runtime without requiring authentication. In a production environment, this would be a per-user setting stored in the database. For demo purposes, we use a simple in-memory session store.

**Request Body**

- Required: yes
- application/json: Body_set_demo_mode_api_v1_settings_demo_post

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | object |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/settings/model-preferences

**Summary**: Get Model Preferences

**Tags**: Settings

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| user_email | query | string \| null | no |  |
| X-User-Email | header | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | ModelPreferences |
| 422 | Validation Error | HTTPValidationError |

## PUT /api/v1/settings/model-preferences

**Summary**: Update Model Preferences

**Tags**: Settings

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| user_email | query | string \| null | no |  |
| X-User-Email | header | string \| null | no |  |

**Request Body**

- Required: yes
- application/json: ModelPreferencesUpdate

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | ModelPreferences |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/settings/models

**Summary**: List Model Catalog

**Tags**: Settings

List available model providers and their models.

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | array[ModelProviderCatalog] |

## GET /api/v1/settings/notifications

**Summary**: Get Notification Settings

**Tags**: Settings

Get notification settings for the current user (Task #86).

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| user_email | query | string \| null | no |  |
| X-User-Email | header | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | NotificationSettings |
| 422 | Validation Error | HTTPValidationError |

## PUT /api/v1/settings/notifications

**Summary**: Update Notification Settings

**Tags**: Settings

Update notification settings for the current user (Task #86).

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| user_email | query | string \| null | no |  |
| X-User-Email | header | string \| null | no |  |

**Request Body**

- Required: yes
- application/json: NotificationSettingsUpdate

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | NotificationSettings |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/settings/notifications/preview

**Summary**: Send Notification Preview

**Tags**: Settings

Send a test notification to verify settings (Task #86).

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| user_email | query | string \| null | no |  |
| X-User-Email | header | string \| null | no |  |

**Request Body**

- Required: yes
- application/json: NotificationPreviewRequest

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | NotificationPreviewResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/settings/notifications/unsubscribe/{token}

**Summary**: Unsubscribe By Token

**Tags**: Settings

One-click unsubscribe from notifications via token (Task #86).

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| token | path | string | yes |  |
| notification_type | query | string \| null | no | Specific type to unsubscribe from, or all if omitted |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | object |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/settings/test-runtime

**Summary**: Test Runtime

**Tags**: Settings

Probe any registered provider's connection/route to readiness. Pre-2026-10-19 this endpoint gated on ``p.is_local`` and rejected every remote provider with HTTP 400. Phase D.6 opens it up: any provider from ``ModelProviderFactory.list_providers()`` can be probed. Local providers (Ollama) still call ``list_available_models()`` to surface the runtime-fetched model list; remote providers return ``available_models=[]`` (they don't expose a runtime-fetched list, only the curated catalog). Operators can now verify Together / Fireworks / HuggingFace / Grok / etc. keys via this endpoint instead of waiting for a real chat request to fail.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| provider | query | string | yes |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | ModelRuntimeTestResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/signatures

**Summary**: List signature requests

**Tags**: E-Signatures

Get paginated list of user's signature requests with optional filtering.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| status | query | string \| null | no |  |
| property_id | query | string \| null | no |  |
| page | query | integer | no |  |
| page_size | query | integer | no |  |
| sort_by | query | string | no |  |
| sort_order | query | string | no |  |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | SignatureRequestListResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/signatures/request

**Summary**: Create a signature request

**Tags**: E-Signatures

Create a new signature request from a template or existing document.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| access_token | cookie | string \| null | no |  |

**Request Body**

- Required: yes
- application/json: SignatureRequestCreate

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 201 | Successful Response | SignatureRequestResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/signatures/templates

**Summary**: List document templates

**Tags**: E-Signatures

Get paginated list of document templates.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| template_type | query | string \| null | no | Filter by template type |
| page | query | integer | no | Page number |
| page_size | query | integer | no | Page size |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | object |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/signatures/templates

**Summary**: Create document template

**Tags**: E-Signatures

Create a new document template with Jinja2 content.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| access_token | cookie | string \| null | no |  |

**Request Body**

- Required: yes
- application/json: DocumentTemplateCreate

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 201 | Successful Response | DocumentTemplateResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/signatures/templates/{template_id}

**Summary**: Get template details

**Tags**: E-Signatures

Get detailed information about a specific template.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| template_id | path | string | yes |  |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | DocumentTemplateResponse |
| 422 | Validation Error | HTTPValidationError |

## PUT /api/v1/signatures/templates/{template_id}

**Summary**: Update template

**Tags**: E-Signatures

Update an existing template.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| template_id | path | string | yes |  |
| access_token | cookie | string \| null | no |  |

**Request Body**

- Required: yes
- application/json: DocumentTemplateUpdate

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | DocumentTemplateResponse |
| 422 | Validation Error | HTTPValidationError |

## DELETE /api/v1/signatures/templates/{template_id}

**Summary**: Delete template

**Tags**: E-Signatures

Delete a document template.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| template_id | path | string | yes |  |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 204 | Successful Response |  |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/signatures/{request_id}

**Summary**: Get signature request details

**Tags**: E-Signatures

Get detailed information about a specific signature request.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| request_id | path | string | yes |  |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | SignatureRequestResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/signatures/{request_id}/cancel

**Summary**: Cancel a signature request

**Tags**: E-Signatures

Cancel a pending signature request.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| request_id | path | string | yes |  |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | object |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/signatures/{request_id}/download

**Summary**: Download signed document

**Tags**: E-Signatures

Download the completed, signed document.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| request_id | path | string | yes |  |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | object |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/signatures/{request_id}/reminder

**Summary**: Send reminder to signers

**Tags**: E-Signatures

Send a reminder email to pending signers.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| request_id | path | string | yes |  |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | object |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/tools

**Summary**: List Tools

**Tags**: Tools, Tools

List available tools.

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | array[ToolInfo] |

## POST /api/v1/tools/advanced-investment-analysis

**Summary**: Calculate Advanced Investment

**Tags**: Tools, Tools

Advanced investment analysis with multi-year projections, tax implications, appreciation scenarios, and risk assessment.

**Request Body**

- Required: yes
- application/json: AdvancedInvestmentInput

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | AdvancedInvestmentResult |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/tools/commute

**Summary**: Osrm Commute Analysis

**Tags**: Tools, Tools

Calculate commute time using OSRM (Open Source Routing Machine). Free alternative to Google Routes API -- no API key required. Supports car, bike, and foot travel modes. Falls back to Haversine estimation when OSRM is unavailable.

**Request Body**

- Required: yes
- application/json: OSRMCommuteRequest

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | OSRMCommuteResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/tools/commute-ranking

**Summary**: Commute Ranking

**Tags**: Tools, Tools

Rank multiple properties by commute time to a destination. Compares commute times from multiple properties to a common destination and returns a ranked list from shortest to longest commute.

**Request Body**

- Required: yes
- application/json: CommuteRankingRequest

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | CommuteRankingResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/tools/commute-time

**Summary**: Commute Time Analysis

**Tags**: Tools, Tools

Calculate commute time from a property to a destination. Uses Google Routes API to calculate accurate commute times including real-time traffic conditions and transit schedules.

**Request Body**

- Required: yes
- application/json: CommuteTimeRequest

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | CommuteTimeResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/tools/compare-properties

**Summary**: Compare Properties

**Tags**: Tools, Tools

**Request Body**

- Required: yes
- application/json: ComparePropertiesRequest

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | ComparePropertiesResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/tools/crm-sync-contact

**Summary**: Crm Sync Contact

**Tags**: Tools, Tools

**Request Body**

- Required: yes
- application/json: CRMContactRequest

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | CRMContactResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/tools/enrich-address

**Summary**: Enrich Address

**Tags**: Tools, Tools

**Request Body**

- Required: yes
- application/json: DataEnrichmentRequest

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | DataEnrichmentResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/tools/generate-listing

**Summary**: Generate Listing

**Tags**: Tools, Tools

Generate AI-powered listing content for a property. Generates: - Property description with customizable tone and language - Multiple headline variants - Platform-specific social media content All generated content respects platform character limits.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| X-User-Email | header | string \| null | no |  |

**Request Body**

- Required: yes
- application/json: ListingGenerationRequest

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | ListingGenerationResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/tools/investment-analysis

**Summary**: Calculate Investment Analysis

**Tags**: Tools, Tools

Calculate investment property metrics including ROI, cap rate, cash flow, and rental yield.

**Request Body**

- Required: yes
- application/json: InvestmentAnalysisInput

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | InvestmentAnalysisResult |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/tools/legal-check

**Summary**: Legal Check

**Tags**: Tools, Tools

**Request Body**

- Required: yes
- application/json: LegalCheckRequest

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | LegalCheckResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/tools/location-analysis

**Summary**: Location Analysis

**Tags**: Tools, Tools

**Request Body**

- Required: yes
- application/json: LocationAnalysisRequest

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | LocationAnalysisResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/tools/mortgage-calculator

**Summary**: Calculate Mortgage

**Tags**: Tools, Tools

Calculate mortgage payments.

**Request Body**

- Required: yes
- application/json: MortgageInput

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | MortgageResult |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/tools/negotiate

**Summary**: Negotiate

**Tags**: Tools, Tools

Analyse market data for a property and suggest a negotiation strategy. Returns: - Fair price band (lower / mid / upper) - Recommended opening offer - Key negotiation arguments - Outreach email template based on selected tone - Legal disclaimer

**Request Body**

- Required: yes
- application/json: NegotiationRequest

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | NegotiationResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/tools/neighborhood-quality

**Summary**: Neighborhood Quality

**Tags**: Tools, Tools

Calculate enhanced neighborhood quality index. Returns scores for 8 factors: - Core: Safety, Schools, Amenities, Walkability, Green Space - New: Air Quality, Noise Level, Public Transport Includes city comparison and nearby POIs for map visualization.

**Request Body**

- Required: yes
- application/json: NeighborhoodQualityInput

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | NeighborhoodQualityResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/tools/neighborhood-summary

**Summary**: Neighborhood Summary

**Tags**: Valuation, Valuation

Return a 2-3 sentence AI summary of a neighborhood.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| X-User-Email | header | string \| null | no |  |

**Request Body**

- Required: yes
- application/json: NeighborhoodSummaryRequest

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | NeighborhoodSummaryResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/tools/portfolio-analysis

**Summary**: Analyze Portfolio

**Tags**: Tools, Tools

Analyze a portfolio of investment properties including aggregate metrics, diversification scores, and risk assessment.

**Request Body**

- Required: yes
- application/json: PortfolioAnalysisInput

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | PortfolioAnalysisResult |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/tools/price-analysis

**Summary**: Price Analysis

**Tags**: Tools, Tools

**Request Body**

- Required: yes
- application/json: PriceAnalysisRequest

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | PriceAnalysisResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/tools/price-forecast

**Summary**: Price Forecast

**Tags**: Valuation, Valuation

Estimate current value and project value at the requested horizons. Either `property_id` (resolved from the vector store) OR `property_features` must be supplied. The LLM returns a structured estimate with confidence and drivers; a deterministic fallback is used if the LLM is unavailable.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| X-User-Email | header | string \| null | no |  |

**Request Body**

- Required: yes
- application/json: PriceForecastRequest

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | PriceForecastResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/tools/rent-vs-buy

**Summary**: Calculate Rent Vs Buy

**Tags**: Tools, Tools

Compare renting vs buying a property over time. Calculates: - Monthly payment comparison - Total cost over time - Break-even point (when buying becomes cheaper) - Opportunity cost of down payment - Tax benefits of ownership - Property appreciation impact

**Request Body**

- Required: yes
- application/json: RentVsBuyInput

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | RentVsBuyResult |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/tools/tco-available-locations

**Summary**: List Tco Available Locations

**Tags**: Tools, Tools

List all available locations with TCO default values. Returns a dictionary mapping country codes to lists of available regions.

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | AvailableLocationsResponse |

## POST /api/v1/tools/tco-calculator

**Summary**: Calculate Tco

**Tags**: Tools, Tools

Calculate Total Cost of Ownership for a property. Includes mortgage, property taxes, insurance, HOA fees, utilities, maintenance, and parking.

**Request Body**

- Required: yes
- application/json: TCOInput

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | TCOResult |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/tools/tco-comparison

**Summary**: Compare Tco

**Tags**: Tools, Tools

Compare Total Cost of Ownership between two property scenarios. Provides: - Side-by-side enhanced TCO analysis with projections - Cost difference calculations (monthly and total) - Break-even analysis (when one scenario becomes better) - Trade-off analysis with pros/cons - Priority-weighted recommendation based on user preferences

**Request Body**

- Required: yes
- application/json: TCOComparisonInput

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | TCOComparisonResult |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/tools/tco-location-defaults

**Summary**: Get Tco Location Defaults

**Tags**: Tools, Tools

Get location-based default cost estimates for TCO Calculator. Returns reasonable default values for: - Property tax rates (annual % of property value) - Insurance rates (annual % of property value) - Utilities per sqm (monthly) - Internet costs (monthly) - Parking costs (monthly) Supports EU (DE, ES, GB, FR, IT, NL) and USA regions.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| country | query | string | yes |  |
| region | query | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | LocationDefaultsResponse |
| 422 | Validation Error | HTTPValidationError |

## POST /api/v1/tools/valuation

**Summary**: Valuation

**Tags**: Tools, Tools

**Request Body**

- Required: yes
- application/json: ValuationRequest

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | ValuationResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/user-activity/admin/summary

**Summary**: Get global activity summary (admin)

**Tags**: User Activity Analytics

Get aggregated activity metrics for all users (admin only).

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| period_start | query | string \| null | no | Start of analysis period (default: 30 days ago) |
| period_end | query | string \| null | no | End of analysis period (default: now) |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | UserActivitySummary |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/user-activity/admin/trends

**Summary**: Get global activity trends (admin)

**Tags**: User Activity Analytics

Get activity trends over time for all users (admin only).

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| interval | query | string | no | Time interval for grouping |
| period_start | query | string \| null | no | Start of analysis period (default: 30 days ago) |
| period_end | query | string \| null | no | End of analysis period (default: now) |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | UserActivityTrendsResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/user-activity/export

**Summary**: Export activity data

**Tags**: User Activity Analytics

Export user activity data as CSV file.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| period_start | query | string \| null | no | Start of analysis period (default: 30 days ago) |
| period_end | query | string \| null | no | End of analysis period (default: now) |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | CSV file with activity data | object |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/user-activity/summary

**Summary**: Get activity summary

**Tags**: User Activity Analytics

Get aggregated activity metrics for the current user.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| period_start | query | string \| null | no | Start of analysis period (default: 30 days ago) |
| period_end | query | string \| null | no | End of analysis period (default: now) |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | UserActivitySummary |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/user-activity/trends

**Summary**: Get activity trends

**Tags**: User Activity Analytics

Get activity trends over time with configurable intervals.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| interval | query | string | no | Time interval for grouping |
| period_start | query | string \| null | no | Start of analysis period (default: 30 days ago) |
| period_end | query | string \| null | no | End of analysis period (default: now) |
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | UserActivityTrendsResponse |
| 422 | Validation Error | HTTPValidationError |

## GET /api/v1/verify-auth

**Summary**: Verify Auth

**Tags**: Auth

Verify API key authentication.

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | object |

## POST /api/v1/webhooks/esignatures/hellosign

**Summary**: Handle HelloSign webhook

**Tags**: Webhooks

Receive and process HelloSign webhook callbacks.

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | object |

## GET /health

**Summary**: Health Check

**Tags**: Monitoring, Monitoring

Liveness probe - checks if the service is alive. Returns 200 if the service is running, regardless of dependencies. Used by Kubernetes/Docker health checks.

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | object |

## GET /health/detailed

**Summary**: Health Check

**Tags**: System

Health check endpoint to verify API status. Args: include_dependencies: Whether to check dependency health (vector store, Redis, LLM providers) Returns: Comprehensive health status including dependencies

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| include_dependencies | query | boolean | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | object |
| 422 | Validation Error | HTTPValidationError |

## GET /health/live

**Summary**: Liveness Check

**Tags**: System

K8s liveness probe - checks if app is alive. Simple ping endpoint (no dependency checks).

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | object |

## GET /health/ready

**Summary**: Readiness Check

**Tags**: System

K8s readiness probe - checks if app can serve traffic. Returns 200 if all critical dependencies are available.

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | object |

## GET /metrics

**Summary**: Metrics Endpoint

**Tags**: System

Prometheus-compatible metrics endpoint (TASK-017). Returns application metrics in Prometheus text format.

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | object |

## GET /monitoring/overview

**Summary**: Monitoring Overview

**Tags**: Monitoring, Monitoring

High-level monitoring overview for admin dashboard. Returns aggregated metrics for the monitoring dashboard UI.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | object |
| 422 | Validation Error | HTTPValidationError |

## POST /monitoring/test-alert

**Summary**: Test Alert

**Tags**: Monitoring, Monitoring

Test alert endpoint for monitoring notifications. Sends a test alert to validate alerting configuration. Requires system admin permission.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | object |
| 422 | Validation Error | HTTPValidationError |

## GET /ready

**Summary**: Readiness Check

**Tags**: Monitoring, Monitoring

Readiness probe - checks if the service is ready to handle requests. Validates database, Redis (if configured), and LLM provider availability. Used by Kubernetes/Docker readiness probes and load balancers.

**Parameters**

| Name | In | Type | Required | Description |
|---|---|---|---|---|
| access_token | cookie | string \| null | no |  |

**Responses**

| Status | Description | Body (application/json) |
|---|---|---|
| 200 | Successful Response | object |
| 422 | Validation Error | HTTPValidationError |
