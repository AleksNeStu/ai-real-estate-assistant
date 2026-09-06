from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator

from data.schemas import Property
from utils.exporters import ExportFormat


class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


class SortField(str, Enum):
    RELEVANCE = "relevance"
    PRICE = "price"
    PRICE_PER_SQM = "price_per_sqm"
    AREA = "area_sqm"
    YEAR_BUILT = "year_built"


# ============================================================================
# TASK-076: Ranking Explanation Models
# ============================================================================


class ScoreComponent(BaseModel):
    """A single component of the final ranking score."""

    name: str = Field(..., description="Component name (e.g., 'semantic_similarity')")
    value: float = Field(..., description="Raw value before weighting")
    weight: float = Field(..., description="Applied weight/boost factor")
    contribution: float = Field(..., description="value * weight")
    description: str = Field(..., description="Human-readable explanation")


class RankingExplanation(BaseModel):
    """Complete ranking explanation for a single property."""

    property_id: str
    final_score: float
    rank: int

    # Core scores
    semantic_score: float = Field(..., description="Vector similarity score (0-1)")
    keyword_score: float = Field(..., description="BM25 keyword score (0-1)")
    hybrid_score: float = Field(..., description="Combined hybrid score")

    # Boost components
    exact_match_boost: float = Field(0.0, description="Boost for exact keyword matches")
    metadata_match_boost: float = Field(0.0, description="Boost for matching user criteria")
    quality_boost: float = Field(0.0, description="Boost for data completeness")
    personalization_boost: float = Field(0.0, description="Boost from user preferences")

    # Penalty components
    diversity_penalty: float = Field(1.0, description="Penalty factor (1.0 = no penalty)")

    # All components as list for detailed breakdown
    components: List[ScoreComponent] = Field(default_factory=list)


class HealthCheck(BaseModel):
    """Health check response model."""

    status: str
    version: str


class AdminVersionInfo(BaseModel):
    version: str
    environment: str
    app_title: str
    python_version: str
    platform: str


class NotificationsAdminStats(BaseModel):
    scheduler_running: bool
    alerts_storage_path: str

    sent_alerts_total: int
    pending_alerts_total: int
    pending_alerts_by_type: Dict[str, int] = Field(default_factory=dict)
    pending_alerts_oldest_created_at: Optional[datetime] = None
    pending_alerts_newest_created_at: Optional[datetime] = None


class SearchRequest(BaseModel):
    """Search request model."""

    query: str
    limit: int = 10
    filters: Optional[Dict[str, Any]] = None
    alpha: float = 0.7

    # Geospatial
    lat: Optional[float] = Field(None, ge=-90, le=90, description="Latitude for geo-search")
    lon: Optional[float] = Field(None, ge=-180, le=180, description="Longitude for geo-search")
    radius_km: Optional[float] = Field(None, gt=0, description="Radius in kilometers")
    min_lat: Optional[float] = Field(None, ge=-90, le=90, description="Bounding box min latitude")
    max_lat: Optional[float] = Field(None, ge=-90, le=90, description="Bounding box max latitude")
    min_lon: Optional[float] = Field(
        None, ge=-180, le=180, description="Bounding box min longitude"
    )
    max_lon: Optional[float] = Field(
        None, ge=-180, le=180, description="Bounding box max longitude"
    )

    # Polygon filter for drawn areas (GeoJSON polygon coordinates)
    polygon: Optional[List[List[float]]] = Field(
        None,
        description="GeoJSON polygon coordinates for geo-search (list of [lon, lat] pairs)",
    )

    # Sorting
    sort_by: Optional[SortField] = SortField.RELEVANCE
    sort_order: Optional[SortOrder] = SortOrder.DESC

    # Ranking explanation (Task #76)
    include_explanation: bool = Field(
        default=False, description="Include ranking explanation in response"
    )


class SearchResultItem(BaseModel):
    """Search result item with score."""

    property: Property
    score: float
    explanation: Optional[RankingExplanation] = Field(
        None, description="Ranking explanation (when include_explanation=True)"
    )


class SearchResponse(BaseModel):
    """Search response model."""

    results: List[SearchResultItem]
    count: int


class ChatRequest(BaseModel):
    """Chat request model."""

    message: str
    session_id: Optional[str] = None
    stream: bool = False
    include_intermediate_steps: bool = False


class ChatResponse(BaseModel):
    """Chat response model."""

    response: str
    sources: List[Dict[str, Any]] = []
    sources_truncated: bool = False
    citation_stats: Optional["CitationStats"] = Field(None, description="Citation statistics")
    session_id: Optional[str] = None
    intermediate_steps: Optional[List[Dict[str, Any]]] = None


class RagCitation(BaseModel):
    source: Optional[str] = None
    chunk_index: Optional[int] = None
    page_number: Optional[int] = None
    paragraph_number: Optional[int] = None


# ============================================================================
# TASK-065: Enhanced Citation Models
# ============================================================================


class SourceType(str, Enum):
    """Type of citation source."""

    PDF = "pdf"
    DOCX = "docx"
    WEB = "web"
    DATABASE = "database"
    API = "api"
    UNKNOWN = "unknown"


class CitationConfidence(str, Enum):
    """Confidence level for citation relevance."""

    HIGH = "high"  # Direct quote match
    MEDIUM = "medium"  # Semantic match
    LOW = "low"  # Partial match


class EnhancedCitation(BaseModel):
    """Enhanced citation with confidence scoring and validation."""

    # Existing fields (backward compatible)
    source: Optional[str] = None
    chunk_index: Optional[int] = None
    page_number: Optional[int] = None
    paragraph_number: Optional[int] = None

    # New fields for enhanced citations
    source_type: SourceType = SourceType.UNKNOWN
    confidence: CitationConfidence = CitationConfidence.MEDIUM
    confidence_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Confidence score 0.0-1.0"
    )
    content_snippet: Optional[str] = Field(None, description="Relevant excerpt from source")
    source_url: Optional[str] = Field(None, description="URL for web sources")
    source_title: Optional[str] = Field(None, description="Human-readable title")
    citation_hash: Optional[str] = Field(None, description="Hash for deduplication")
    is_duplicate: bool = Field(default=False, description="Whether this is a duplicate citation")
    validated: bool = Field(
        default=False, description="Whether citation was validated against source"
    )

    def to_legacy_citation(self) -> RagCitation:
        """Convert to legacy RagCitation for backward compatibility."""
        return RagCitation(
            source=self.source,
            chunk_index=self.chunk_index,
            page_number=self.page_number,
            paragraph_number=self.paragraph_number,
        )


class CitationStats(BaseModel):
    """Statistics about citations in a response."""

    total: int = Field(..., ge=0, description="Total number of citations")
    unique: int = Field(..., ge=0, description="Number of unique citations")
    duplicates: int = Field(..., ge=0, description="Number of duplicate citations")
    by_type: Dict[str, int] = Field(default_factory=dict, description="Count by source type")
    avg_confidence: float = Field(..., ge=0.0, le=1.0, description="Average confidence score")


class RagQaRequest(BaseModel):
    question: str = Field(..., min_length=1)
    top_k: int = Field(5, ge=1, le=50)
    provider: Optional[str] = None
    model: Optional[str] = None
    citation_format: str = Field(
        default="inline", description="Citation format style: inline, footnote, or endnote"
    )
    stream: bool = Field(default=False, description="Enable SSE streaming of response chunks")


class RagQaResponse(BaseModel):
    answer: str
    citations: List[EnhancedCitation] = Field(default_factory=list)
    citation_format: str = Field(default="inline", description="Citation format style used")
    citation_stats: Optional[CitationStats] = Field(None, description="Citation statistics")
    llm_used: bool = False
    provider: Optional[str] = None
    model: Optional[str] = None


class RagResetResponse(BaseModel):
    message: str
    documents_removed: int
    documents_remaining: int


class IngestRequest(BaseModel):
    """Request model for data ingestion."""

    file_urls: Optional[List[str]] = None
    force: bool = False
    # Excel-specific options
    sheet_name: Optional[str] = Field(
        None, description="Excel sheet name to load (for .xlsx, .xls, .ods files)"
    )
    header_row: Optional[int] = Field(
        0, ge=0, description="Header row number for Excel files (0-indexed)"
    )
    source_name: Optional[str] = Field(
        None, description="Optional source name for tracking (e.g., 'properties_2024_q1')"
    )


class IngestResponse(BaseModel):
    """Response model for data ingestion."""

    message: str
    properties_processed: int
    errors: List[str] = []
    source_type: Optional[str] = None
    source_name: Optional[str] = None


class ExcelSheetsRequest(BaseModel):
    """Request model for getting Excel sheet names."""

    file_url: str = Field(..., description="URL to Excel file")


class ExcelSheetsResponse(BaseModel):
    """Response model for Excel sheet names."""

    file_url: str
    sheet_names: List[str]
    default_sheet: Optional[str] = None
    row_count: Dict[str, int] = Field(default_factory=dict, description="Row count per sheet")


class ReindexRequest(BaseModel):
    """Request model for reindexing."""

    clear_existing: bool = False


class ReindexResponse(BaseModel):
    """Response model for reindexing."""

    message: str
    count: int


class NotificationSettings(BaseModel):
    """User notification settings (Task #86)."""

    # Notification type toggles
    price_alerts_enabled: bool = True
    new_listings_enabled: bool = True
    saved_search_enabled: bool = True
    market_updates_enabled: bool = False

    # Frequency settings
    alert_frequency: str = "daily"  # instant, daily, weekly

    # Channel selection
    email_enabled: bool = True
    push_enabled: bool = False
    in_app_enabled: bool = True

    # Advanced settings
    quiet_hours_start: Optional[str] = None  # HH:MM format
    quiet_hours_end: Optional[str] = None  # HH:MM format
    price_drop_threshold: float = 5.0  # percentage

    # Digest settings
    daily_digest_time: str = "09:00"
    weekly_digest_day: str = "monday"

    # Expert/Marketing preferences
    expert_mode: bool = False
    marketing_emails: bool = False

    # Unsubscribe info (read-only)
    unsubscribe_token: Optional[str] = None
    unsubscribed_at: Optional[datetime] = None
    unsubscribed_types: Optional[List[str]] = None


class NotificationSettingsUpdate(BaseModel):
    """Update payload for notification settings (partial updates allowed)."""

    # Notification type toggles
    price_alerts_enabled: Optional[bool] = None
    new_listings_enabled: Optional[bool] = None
    saved_search_enabled: Optional[bool] = None
    market_updates_enabled: Optional[bool] = None

    # Frequency settings
    alert_frequency: Optional[str] = None

    # Channel selection
    email_enabled: Optional[bool] = None
    push_enabled: Optional[bool] = None
    in_app_enabled: Optional[bool] = None

    # Advanced settings
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None
    price_drop_threshold: Optional[float] = None

    # Digest settings
    daily_digest_time: Optional[str] = None
    weekly_digest_day: Optional[str] = None

    # Expert/Marketing preferences
    expert_mode: Optional[bool] = None
    marketing_emails: Optional[bool] = None


class NotificationPreviewRequest(BaseModel):
    """Request to send a test notification."""

    channel: str = "email"  # email, push, in_app
    notification_type: str = "price_alert"  # price_alert, new_listing, etc.


class NotificationPreviewResponse(BaseModel):
    """Response after sending a test notification."""

    success: bool
    message: str
    channel: str
    notification_type: str


class ModelPricing(BaseModel):
    input_price_per_1m: float
    output_price_per_1m: float
    currency: str = "USD"


class ModelCatalogItem(BaseModel):
    id: str
    display_name: str
    provider_name: str
    context_window: int
    pricing: Optional[ModelPricing] = None
    capabilities: List[str] = Field(default_factory=list)
    description: Optional[str] = None
    recommended_for: List[str] = Field(default_factory=list)


class ModelProviderCatalog(BaseModel):
    name: str
    display_name: str
    is_local: bool
    requires_api_key: bool
    models: List[ModelCatalogItem]
    runtime_available: Optional[bool] = None
    available_models: Optional[List[str]] = None
    runtime_error: Optional[str] = None


class ModelRuntimeTestResponse(BaseModel):
    provider: str
    is_local: bool
    runtime_available: Optional[bool] = None
    available_models: Optional[List[str]] = None
    runtime_error: Optional[str] = None


class ModelPreferences(BaseModel):
    preferred_provider: Optional[str] = None
    preferred_model: Optional[str] = None


class ModelPreferencesUpdate(BaseModel):
    preferred_provider: Optional[str] = None
    preferred_model: Optional[str] = None

    @model_validator(mode="after")
    def validate_not_empty(self) -> "ModelPreferencesUpdate":
        if self.preferred_provider is None and self.preferred_model is None:
            raise ValueError(
                "At least one of preferred_provider or preferred_model must be provided"
            )
        return self


class ComparePropertiesRequest(BaseModel):
    property_ids: List[str]


class ComparedProperty(BaseModel):
    id: Optional[str] = None
    price: Optional[float] = None
    price_per_sqm: Optional[float] = None
    city: Optional[str] = None
    rooms: Optional[float] = None
    bathrooms: Optional[float] = None
    area_sqm: Optional[float] = None
    year_built: Optional[int] = None
    property_type: Optional[str] = None


class CompareSummary(BaseModel):
    count: int
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    price_difference: Optional[float] = None


class ComparePropertiesResponse(BaseModel):
    properties: List[ComparedProperty]
    summary: CompareSummary


class PriceAnalysisRequest(BaseModel):
    query: str


class PriceAnalysisResponse(BaseModel):
    query: str
    count: int
    average_price: Optional[float] = None
    median_price: Optional[float] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    average_price_per_sqm: Optional[float] = None
    median_price_per_sqm: Optional[float] = None
    distribution_by_type: Dict[str, int] = {}


class LocationAnalysisRequest(BaseModel):
    property_id: str


class LocationAnalysisResponse(BaseModel):
    property_id: str
    city: Optional[str] = None
    neighborhood: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None


class ValuationRequest(BaseModel):
    property_id: str


class ValuationResponse(BaseModel):
    property_id: str
    estimated_value: float


# ============================================================================
# v5.1: AI Price Forecast with Multi-Year Projection
# ============================================================================


class PriceForecastRequest(BaseModel):
    """Request for AI price forecast.

    Either property_id OR property_features must be provided.
    """

    property_id: Optional[str] = Field(
        default=None, description="Existing property id (resolved from vector store)"
    )
    property_features: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Free-form property features for hypothetical scenarios",
    )
    horizon_years: List[int] = Field(
        default_factory=lambda: [1, 3, 5],
        description="Forecast horizons in years (each must be in [1, 10])",
    )


class ForecastPointResponse(BaseModel):
    years_ahead: int
    estimated_value: float
    lower_bound: float
    upper_bound: float


class PriceForecastResponse(BaseModel):
    current_estimate: float
    currency: str = "EUR"
    horizon_years: List[int]
    forecast: List[ForecastPointResponse]
    confidence: float
    drivers: List[str] = Field(default_factory=list)
    explanation: str
    comparables_used: int = 0
    median_price_per_sqm: Optional[float] = None
    neighborhood_median_price_per_sqm: Optional[float] = None
    disclaimer: str = (
        "AI estimate, not a formal appraisal. Forecasts are scenario-based "
        "and depend on market conditions that may change."
    )


class NeighborhoodSummaryRequest(BaseModel):
    city: Optional[str] = None
    neighborhood: Optional[str] = None
    property_type: Optional[str] = None
    rooms: Optional[float] = None
    area_sqm: Optional[float] = None
    language: str = "en"
    max_sentences: int = Field(default=3, ge=1, le=5)


class NeighborhoodSummaryResponse(BaseModel):
    summary: str
    language: str = "en"


class LegalCheckRequest(BaseModel):
    text: str


class LegalCheckResponse(BaseModel):
    risks: List[Dict[str, Any]] = []
    score: float = 0.0


class DataEnrichmentRequest(BaseModel):
    address: str


class DataEnrichmentResponse(BaseModel):
    address: str
    data: Dict[str, Any] = {}


class CRMContactRequest(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None


class CRMContactResponse(BaseModel):
    id: str


class ExportPropertiesRequest(BaseModel):
    format: ExportFormat
    property_ids: Optional[List[str]] = None
    search: Optional[SearchRequest] = None

    columns: Optional[List[str]] = None
    include_header: bool = True
    csv_delimiter: str = ","
    csv_decimal: str = "."

    include_summary: bool = True
    include_statistics: bool = True
    include_metadata: bool = True
    pretty: bool = True
    max_properties: Optional[int] = None

    @model_validator(mode="after")
    def validate_input(self) -> "ExportPropertiesRequest":
        if not self.property_ids and self.search is None:
            raise ValueError("Either property_ids or search must be provided")
        if len(self.csv_delimiter) != 1 or self.csv_delimiter in ("\n", "\r"):
            raise ValueError("csv_delimiter must be a single non-newline character")
        if len(self.csv_decimal) != 1 or self.csv_decimal in ("\n", "\r"):
            raise ValueError("csv_decimal must be a single non-newline character")
        return self


class PromptTemplateVariableInfo(BaseModel):
    name: str
    description: str
    required: bool = True
    example: Optional[str] = None


class PromptTemplateInfo(BaseModel):
    id: str
    title: str
    category: str
    description: str
    template_text: str
    variables: List[PromptTemplateVariableInfo]


class PromptTemplateApplyRequest(BaseModel):
    template_id: str
    variables: Dict[str, Any] = Field(default_factory=dict)


class PromptTemplateApplyResponse(BaseModel):
    template_id: str
    rendered_text: str


# SSE Event Models for TASK-003.1
class SSEContentEvent(BaseModel):
    """SSE content chunk event."""

    content: str


class SSEErrorEvent(BaseModel):
    """SSE error event for streaming failures."""

    error: str
    request_id: Optional[str] = None


class SSEMetaEvent(BaseModel):
    """SSE meta event with sources and session info."""

    sources: List[Dict[str, Any]] = Field(default_factory=list)
    sources_truncated: bool = False
    session_id: str
    request_id: Optional[str] = None
    intermediate_steps: Optional[List[Dict[str, Any]]] = None


# Portal/API Integration Models for TASK-006
class PortalFiltersRequest(BaseModel):
    """Request model for portal data fetching with filters."""

    portal: str = Field(..., description="Portal adapter name (e.g., 'otodom', 'idealista')")
    city: Optional[str] = Field(None, description="City to search in")
    min_price: Optional[float] = Field(None, ge=0, description="Minimum price filter")
    max_price: Optional[float] = Field(None, ge=0, description="Maximum price filter")
    min_rooms: Optional[float] = Field(None, ge=0, description="Minimum number of rooms")
    max_rooms: Optional[float] = Field(None, ge=0, description="Maximum number of rooms")
    property_type: Optional[str] = Field(None, description="Property type (apartment, house, etc.)")
    listing_type: Optional[str] = Field("rent", description="Listing type (rent, sale)")
    limit: int = Field(100, ge=1, le=500, description="Maximum results to fetch")
    source_name: Optional[str] = Field(
        None, description="Optional source name for tracking (e.g., 'warsaw_rentals')"
    )


class PortalIngestResponse(BaseModel):
    """Response model for portal data ingestion."""

    success: bool
    message: str
    portal: str
    properties_processed: int
    source_type: str = "portal"
    source_name: Optional[str] = None
    errors: List[str] = Field(default_factory=list)
    filters_applied: Optional[Dict[str, Any]] = None


class PortalAdapterInfo(BaseModel):
    """Information about a portal adapter."""

    name: str
    display_name: str
    configured: bool
    has_api_key: bool = False
    rate_limit: Optional[Dict[str, int]] = None


class PortalAdaptersResponse(BaseModel):
    """Response model for listing available portal adapters."""

    adapters: List[PortalAdapterInfo]
    count: int


# Investment Analysis Models for TASK-019
class InvestmentAnalysisRequest(BaseModel):
    """Request model for investment property analysis."""

    property_price: float = Field(..., gt=0, description="Purchase price of the property")
    monthly_rent: float = Field(..., gt=0, description="Expected monthly rental income")
    down_payment_percent: float = Field(
        default=20.0, ge=0, le=100, description="Down payment percentage"
    )
    closing_costs: float = Field(default=0.0, ge=0, description="Closing costs (one-time)")
    renovation_costs: float = Field(default=0.0, ge=0, description="Renovation costs (one-time)")
    interest_rate: float = Field(default=4.5, ge=0, description="Annual interest rate percentage")
    loan_years: int = Field(default=30, gt=0, le=50, description="Loan term in years")
    property_tax_monthly: float = Field(default=0.0, ge=0, description="Monthly property tax")
    insurance_monthly: float = Field(default=0.0, ge=0, description="Monthly insurance")
    hoa_monthly: float = Field(default=0.0, ge=0, description="Monthly HOA fees")
    maintenance_percent: float = Field(
        default=1.0, ge=0, description="Annual maintenance percentage of property value"
    )
    vacancy_rate: float = Field(default=5.0, ge=0, le=100, description="Vacancy rate percentage")
    management_percent: float = Field(
        default=0.0, ge=0, description="Property management fee percentage of rent"
    )


class InvestmentAnalysisResponse(BaseModel):
    """Response model for investment property analysis."""

    monthly_cash_flow: float
    annual_cash_flow: float
    cash_on_cash_roi: float
    cap_rate: float
    gross_yield: float
    net_yield: float
    total_investment: float
    monthly_income: float
    monthly_expenses: float
    annual_income: float
    annual_expenses: float
    monthly_mortgage: float
    investment_score: float
    score_breakdown: Dict[str, float]


class CompareInvestmentsRequest(BaseModel):
    """Request model for comparing investment properties."""

    property_ids: List[str]


class ComparedInvestmentProperty(BaseModel):
    """Investment comparison data for a single property."""

    property_id: Optional[str] = None
    price: Optional[float] = None
    monthly_rent: Optional[float] = None
    monthly_cash_flow: Optional[float] = None
    cash_on_cash_roi: Optional[float] = None
    cap_rate: Optional[float] = None
    investment_score: Optional[float] = None


class CompareInvestmentsResponse(BaseModel):
    """Response model for investment property comparison."""

    properties: List[ComparedInvestmentProperty]
    summary: Dict[str, Any] = Field(default_factory=dict)


# Neighborhood Quality Index Models for TASK-020
# ============================================================================
# TASK-040: Enhanced Neighborhood Quality Models
# ============================================================================


class FactorDetail(BaseModel):
    """Detailed breakdown for a scoring factor."""

    raw_value: Optional[float] = Field(None, description="Original measurement value")
    unit: str = Field(default="", description="Unit of measurement (e.g., 'count', 'AQI')")
    normalized_score: float = Field(..., ge=0, le=100, description="Normalized score 0-100")
    weight: float = Field(..., ge=0, le=1, description="Weight in overall score")
    weighted_score: float = Field(..., description="Score × weight")
    data_source: str = Field(default="", description="Source of the data")
    confidence: float = Field(default=0.5, ge=0, le=1, description="Data quality confidence 0-1")


class CityComparison(BaseModel):
    """Comparison to city average scores."""

    city_name: str
    city_average_score: float = Field(..., description="City's overall average score")
    percentile: int = Field(..., ge=0, le=100, description="Property's percentile in city")
    better_than: List[str] = Field(
        default_factory=list, description="Factors better than city average"
    )
    worse_than: List[str] = Field(
        default_factory=list, description="Factors worse than city average"
    )
    factor_comparison: Optional[Dict[str, Dict[str, float]]] = Field(
        None, description="Detailed factor-by-factor comparison"
    )


class NearbyPOI(BaseModel):
    """A nearby point of interest."""

    id: str
    name: Optional[str] = None
    type: str
    category: str = Field(..., description="Category: school, amenity, green_space, transport")
    latitude: float
    longitude: float
    distance_m: Optional[float] = Field(None, description="Distance in meters")


class NearbyPOIs(BaseModel):
    """Collection of nearby POIs for map visualization."""

    schools: List[NearbyPOI] = Field(default_factory=list)
    amenities: List[NearbyPOI] = Field(default_factory=list)
    green_spaces: List[NearbyPOI] = Field(default_factory=list)
    transport_stops: List[NearbyPOI] = Field(default_factory=list)
    police_stations: List[NearbyPOI] = Field(default_factory=list)


class NeighborhoodQualityRequest(BaseModel):
    """Request model for neighborhood quality analysis."""

    property_id: str = Field(..., min_length=1, description="Property ID to analyze")
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Latitude coordinate")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Longitude coordinate")
    city: Optional[str] = Field(None, description="City name for data enrichment")
    neighborhood: Optional[str] = Field(None, description="Neighborhood name")
    custom_weights: Optional[Dict[str, float]] = Field(
        None,
        description="Custom weights for scoring factors (must sum to 1.0)",
    )
    compare_to_city_average: bool = Field(
        True,
        description="Include comparison to city average scores",
    )
    include_pois: bool = Field(
        True,
        description="Include nearby POIs for map visualization",
    )


class NeighborhoodQualityResponse(BaseModel):
    """Response model for neighborhood quality analysis."""

    property_id: str
    overall_score: float = Field(
        ..., ge=0, le=100, description="Overall neighborhood quality score (0-100)"
    )
    # Core factors (existing)
    safety_score: float = Field(..., ge=0, le=100, description="Safety score (0-100)")
    schools_score: float = Field(..., ge=0, le=100, description="Schools score (0-100)")
    amenities_score: float = Field(..., ge=0, le=100, description="Amenities score (0-100)")
    walkability_score: float = Field(..., ge=0, le=100, description="Walkability score (0-100)")
    green_space_score: float = Field(..., ge=0, le=100, description="Green space score (0-100)")
    # New factors (Task #40)
    air_quality_score: Optional[float] = Field(
        None, ge=0, le=100, description="Air quality score (0-100)"
    )
    noise_level_score: Optional[float] = Field(
        None, ge=0, le=100, description="Noise level/quietness score (0-100)"
    )
    public_transport_score: Optional[float] = Field(
        None, ge=0, le=100, description="Public transport accessibility score (0-100)"
    )
    # Detailed breakdown
    score_breakdown: Dict[str, float] = Field(
        default_factory=dict, description="Detailed scoring breakdown with weights"
    )
    factor_details: Optional[Dict[str, FactorDetail]] = Field(
        None, description="Detailed information for each factor"
    )
    # City comparison
    city_comparison: Optional[CityComparison] = Field(
        None, description="Comparison to city average scores"
    )
    # POIs for map
    nearby_pois: Optional[NearbyPOIs] = Field(None, description="Nearby POIs for map visualization")
    # Metadata
    data_sources: List[str] = Field(
        default_factory=list, description="Data sources used for scoring"
    )
    data_freshness: Optional[Dict[str, str]] = Field(
        None, description="Timestamp of data fetch per source"
    )
    # Location
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    city: Optional[str] = None
    neighborhood: Optional[str] = None


# ============================================================================
# TASK-021: Commute Time Analysis Models
# ============================================================================


class CommuteTimeRequest(BaseModel):
    """Request model for commute time analysis."""

    property_id: str = Field(..., min_length=1, description="Property ID to analyze commute from")
    destination_lat: float = Field(..., ge=-90, le=90, description="Destination latitude")
    destination_lon: float = Field(..., ge=-180, le=180, description="Destination longitude")
    mode: str = Field(
        default="transit",
        description="Commute mode: 'driving', 'walking', 'bicycling', or 'transit'",
    )
    destination_name: Optional[str] = Field(
        None, description="Optional destination name for display"
    )
    departure_time: Optional[str] = Field(
        None, description="Optional departure time as ISO string (e.g., '2024-01-15T08:30:00')"
    )


class CommuteTimeResult(BaseModel):
    """Single property commute time result."""

    property_id: str
    origin_lat: float
    origin_lon: float
    destination_lat: float
    destination_lon: float
    destination_name: Optional[str] = None
    duration_seconds: int = Field(..., description="Commute duration in seconds")
    duration_text: str = Field(..., description="Human-readable duration (e.g., '45m')")
    distance_meters: int = Field(..., description="Distance in meters")
    distance_text: str = Field(..., description="Human-readable distance (e.g., '12.5km')")
    mode: str
    polyline: Optional[str] = Field(None, description="Encoded polyline for route visualization")
    arrival_time: Optional[str] = None
    departure_time: Optional[str] = None


class CommuteTimeResponse(BaseModel):
    """Response model for commute time analysis."""

    result: CommuteTimeResult


class CommuteRankingRequest(BaseModel):
    """Request model for commute-based property ranking."""

    property_ids: str = Field(
        ..., min_length=1, description="Comma-separated list of property IDs to rank"
    )
    destination_lat: float = Field(..., ge=-90, le=90, description="Destination latitude")
    destination_lon: float = Field(..., ge=-180, le=180, description="Destination longitude")
    mode: str = Field(
        default="transit",
        description="Commute mode: 'driving', 'walking', 'bicycling', or 'transit'",
    )
    destination_name: Optional[str] = Field(
        None, description="Optional destination name for display"
    )
    departure_time: Optional[str] = Field(
        None, description="Optional departure time as ISO string (e.g., '2024-01-15T08:30:00')"
    )


class CommuteRankingResponse(BaseModel):
    """Response model for commute-based property ranking."""

    destination_name: Optional[str] = None
    destination_lat: float
    destination_lon: float
    mode: str
    rankings: List[CommuteTimeResult]
    count: int = Field(..., description="Number of properties ranked")
    fastest_duration_seconds: Optional[int] = None
    slowest_duration_seconds: Optional[int] = None


# ============================================================================
# TASK-079: Data Sources Management Models
# ============================================================================


class DataSourceType(str, Enum):
    """Type of data source."""

    FILE_UPLOAD = "file_upload"
    URL = "url"
    PORTAL_API = "portal_api"
    JSON = "json"


class DataSourceStatus(str, Enum):
    """Status of a data source."""

    PENDING = "pending"
    ACTIVE = "active"
    SYNCING = "syncing"
    ERROR = "error"
    DISABLED = "disabled"


class SyncStatus(str, Enum):
    """Status of a sync operation."""

    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


class DataSourceCreate(BaseModel):
    """Request model for creating a data source."""

    name: str = Field(..., min_length=1, max_length=255, description="Display name")
    description: Optional[str] = Field(None, description="Optional description")
    source_type: DataSourceType = Field(..., description="Type of data source")
    config: Dict[str, Any] = Field(
        ...,
        description=(
            "Source configuration. For file_upload: {filename, size_bytes}. "
            "For url: {url, sheet_name?, header_row?}. "
            "For portal_api: {portal, city, filters?}"
        ),
    )
    auto_sync_enabled: bool = Field(default=False, description="Enable automatic sync")
    sync_schedule: Optional[str] = Field(
        None, description="Cron expression for scheduling (e.g., '0 0 * * *' for daily)"
    )


class DataSourceUpdate(BaseModel):
    """Request model for updating a data source."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    auto_sync_enabled: Optional[bool] = None
    sync_schedule: Optional[str] = None
    status: Optional[DataSourceStatus] = None


class DataSourceResponse(BaseModel):
    """Response model for a single data source."""

    id: str
    name: str
    description: Optional[str] = None
    source_type: str
    config: Dict[str, Any]
    status: str
    last_sync_at: Optional[datetime] = None
    last_sync_status: Optional[str] = None
    last_sync_duration_ms: Optional[int] = None
    last_error: Optional[str] = None
    total_records: int
    last_records_synced: Optional[int] = None
    health_score: float
    consecutive_failures: int
    auto_sync_enabled: bool
    sync_schedule: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class DataSourceListResponse(BaseModel):
    """Response model for listing data sources."""

    sources: List[DataSourceResponse]
    total: int
    page: int
    page_size: int


class DataSourceSyncRequest(BaseModel):
    """Request model for triggering a sync."""

    source_id: str = Field(..., description="ID of the data source to sync")


class DataSourceSyncResponse(BaseModel):
    """Response model for sync operation."""

    source_id: str
    status: str
    message: str
    records_processed: int = 0
    started_at: datetime


class DataSourceTestRequest(BaseModel):
    """Request model for testing connection."""

    source_type: DataSourceType
    config: Dict[str, Any] = Field(
        ...,
        description=(
            "Configuration to test. For url: {url, sheet_name?}. "
            "For portal_api: {portal, city, filters?}"
        ),
    )


class DataSourceTestResponse(BaseModel):
    """Response model for connection test."""

    success: bool
    message: str
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional details (e.g., sheet names, row count)"
    )


class SyncHistoryItem(BaseModel):
    """Single sync history item."""

    id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str
    records_processed: int
    records_added: int
    records_updated: int
    records_skipped: int
    error_message: Optional[str] = None


class SyncHistoryResponse(BaseModel):
    """Response model for sync history."""

    source_id: str
    history: List[SyncHistoryItem]
    total: int


# ============================================================================
# TASK-080: Bulk Import/Export Job Models
# ============================================================================


class BulkJobType(str, Enum):
    """Type of bulk job."""

    IMPORT = "import"
    EXPORT = "export"


class BulkJobSourceType(str, Enum):
    """Source type for bulk jobs."""

    URL = "url"
    FILE_UPLOAD = "file_upload"
    PORTAL_API = "portal_api"
    SEARCH = "search"


class BulkJobStatus(str, Enum):
    """Status of a bulk job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BulkImportRequest(BaseModel):
    """Request model for starting a bulk import job."""

    source_type: BulkJobSourceType = Field(..., description="Type of import source")
    config: Dict[str, Any] = Field(
        ...,
        description=(
            "Import configuration. For url: {file_urls, sheet_name?, "
            "header_row?}. For file_upload: {temp_file_path, filename}. "
            "For portal_api: {portal, city, filters?}"
        ),
    )
    source_name: Optional[str] = Field(None, description="Optional name for tracking the import")


class BulkExportRequest(BaseModel):
    """Request model for starting a bulk export job."""

    format: str = Field(..., description="Export format: csv, json, excel, parquet, markdown, pdf")
    source_type: BulkJobSourceType = Field(
        default=BulkJobSourceType.SEARCH, description="Source type for export"
    )
    config: Dict[str, Any] = Field(
        ...,
        description=(
            "Export configuration. For search: {query, filters?, limit?}. "
            "For property_ids: {property_ids}"
        ),
    )
    columns: Optional[List[str]] = Field(None, description="Columns to include in export")
    include_header: bool = Field(default=True, description="Include header row")


class BulkJobResponse(BaseModel):
    """Response model for a single bulk job."""

    id: str
    job_type: str
    source_type: str
    status: str
    records_total: int
    records_processed: int
    records_failed: int
    progress_percent: float
    result_url: Optional[str] = None
    result_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class BulkJobListResponse(BaseModel):
    """Response model for listing bulk jobs."""

    jobs: List[BulkJobResponse]
    total: int
    page: int
    page_size: int


class BulkJobCreateResponse(BaseModel):
    """Response model after creating a bulk job."""

    id: str
    job_type: str
    status: str
    message: str
    created_at: datetime


# ============================================================================
# Task #115: Negotiation Helper
# ============================================================================


class NegotiationRequest(BaseModel):
    """Request model for negotiation analysis."""

    property_identifier: str = Field(
        ...,
        min_length=1,
        description="Property ID or address to analyse",
    )
    user_budget: Optional[float] = Field(
        default=None,
        gt=0,
        description="Buyer's maximum budget",
    )
    tone: str = Field(
        default="formal",
        description="Tone for outreach template: formal, friendly, or assertive",
    )


class NegotiationPriceBand(BaseModel):
    """Suggested price band."""

    lower: Optional[float] = None
    mid: Optional[float] = None
    upper: Optional[float] = None
    user_budget: Optional[float] = None


class NegotiationPropertyInfo(BaseModel):
    """Summary of the analysed property."""

    id: Optional[str] = None
    city: Optional[str] = None
    property_type: Optional[str] = None
    rooms: Optional[Any] = None
    area_sqm: Optional[float] = None
    asking_price: Optional[float] = None


class NegotiationResponse(BaseModel):
    """Response model for negotiation analysis."""

    property: NegotiationPropertyInfo
    price_band: NegotiationPriceBand
    opening_offer: Optional[float] = None
    arguments: List[str] = []
    email_template: Optional[str] = None
    disclaimer: str
