"""Pydantic schemas for authentication API."""

import re
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    """Schema for user registration."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, max_length=128, description="User password")
    full_name: Optional[str] = Field(None, max_length=255, description="User full name")
    consent_given: bool = Field(
        False,
        description="Whether the visitor agreed to the processing of their data at sign-up",
    )

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserLogin(BaseModel):
    """Schema for user login."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class UserUpdate(BaseModel):
    """Schema for user profile update."""

    full_name: Optional[str] = Field(None, max_length=255)
    email: Optional[EmailStr] = None


class UserResponse(BaseModel):
    """Schema for user response."""

    id: str
    email: str
    full_name: Optional[str] = None
    is_active: bool = True
    is_verified: bool = False
    role: str = "user"
    created_at: datetime
    last_login_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# =============================================================================
# Profile Management Schemas (Task #88)
# =============================================================================


class ProfileUpdate(BaseModel):
    """Schema for profile update (partial)."""

    full_name: Optional[str] = Field(None, max_length=255, description="User full name")
    phone: Optional[str] = Field(None, max_length=50, description="Phone number")
    bio: Optional[str] = Field(None, max_length=1000, description="User biography")
    timezone: Optional[str] = Field(
        None, max_length=50, description="User timezone (e.g., 'Europe/Warsaw')"
    )
    language: Optional[str] = Field(
        None, max_length=10, description="Preferred language code (e.g., 'en', 'pl')"
    )

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        """Validate phone number format (optional)."""
        if v is None:
            return v
        # Basic phone validation: allow digits, spaces, dashes, parentheses, plus
        import re

        cleaned = re.sub(r"[^\d\s\-\(\)\+]", "", v)
        if len(re.sub(r"\D", "", cleaned)) < 7:
            raise ValueError("Phone number must contain at least 7 digits")
        return v.strip() if v else None

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: Optional[str]) -> Optional[str]:
        """Validate timezone is a valid IANA timezone."""
        if v is None:
            return v
        # List of common timezones (not exhaustive, but covers most cases)
        valid_timezones = {
            "UTC",
            "GMT",
            # Europe
            "Europe/Warsaw",
            "Europe/London",
            "Europe/Paris",
            "Europe/Berlin",
            "Europe/Moscow",
            "Europe/Kiev",
            "Europe/Prague",
            "Europe/Vienna",
            "Europe/Rome",
            "Europe/Madrid",
            "Europe/Amsterdam",
            "Europe/Brussels",
            "Europe/Stockholm",
            "Europe/Oslo",
            "Europe/Copenhagen",
            "Europe/Helsinki",
            "Europe/Zurich",
            "Europe/Athens",
            "Europe/Istanbul",
            # Americas
            "America/New_York",
            "America/Chicago",
            "America/Denver",
            "America/Los_Angeles",
            "America/San_Francisco",
            "America/Seattle",
            "America/Toronto",
            "America/Vancouver",
            "America/Mexico_City",
            "America/Sao_Paulo",
            "America/Buenos_Aires",
            "America/Bogota",
            # Asia
            "Asia/Tokyo",
            "Asia/Shanghai",
            "Asia/Beijing",
            "Asia/Hong_Kong",
            "Asia/Singapore",
            "Asia/Seoul",
            "Asia/Taipei",
            "Asia/Bangkok",
            "Asia/Jakarta",
            "Asia/Dubai",
            # Africa
            "Africa/Cairo",
            "Africa/Lagos",
            "Africa/Johannesburg",
            # Australia
            "Australia/Sydney",
            "Australia/Melbourne",
            "Australia/Brisbane",
            "Australia/Perth",
        }
        if v not in valid_timezones:
            # Allow any IANA timezone format, but warn if uncommon
            import re

            if not re.match(r"^[A-Za-z_]+/[A-Za-z_]+$", v) and v not in ("UTC", "GMT"):
                raise ValueError(f"Invalid timezone format: {v}")
        return v

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: Optional[str]) -> Optional[str]:
        """Validate language code."""
        if v is None:
            return v
        # Common ISO 639-1 language codes
        valid_codes = {
            "en",
            "pl",
            "de",
            "fr",
            "es",
            "it",
            "pt",
            "nl",
            "ru",
            "uk",
            "cs",
            "sv",
            "da",
            "no",
            "fi",
            "el",
            "tr",
            "ar",
            "he",
            "zh",
            "ja",
            "ko",
            "hi",
            "bn",
            "id",
            "ms",
            "th",
            "vi",
            "ro",
            "hu",
        }
        normalized = v.lower().strip()
        if normalized not in valid_codes:
            raise ValueError(f"Unsupported language code: {v}")
        return normalized


class PrivacySettingsUpdate(BaseModel):
    """Schema for privacy settings update."""

    profile_visible: bool = Field(
        default=True, description="Whether profile is visible to other users"
    )
    activity_visible: bool = Field(
        default=False, description="Whether activity is visible to other users"
    )
    show_email: bool = Field(default=False, description="Whether email is shown on profile")
    show_phone: bool = Field(default=False, description="Whether phone is shown on profile")
    allow_contact: bool = Field(default=True, description="Whether other users can send messages")


class PrivacySettings(BaseModel):
    """Schema for privacy settings response."""

    profile_visible: bool = True
    activity_visible: bool = False
    show_email: bool = False
    show_phone: bool = False
    allow_contact: bool = True


class ProfileResponse(UserResponse):
    """Extended profile response with all profile fields."""

    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    timezone: str = "UTC"
    language: str = "en"
    bio: Optional[str] = None
    privacy_settings: dict = Field(
        default_factory=lambda: {"profile_visible": True, "activity_visible": False}
    )
    gdpr_consent_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AvatarUploadResponse(BaseModel):
    """Schema for avatar upload response."""

    avatar_url: str
    message: str = "Avatar uploaded successfully"


class DataExportRequest(BaseModel):
    """Schema for requesting GDPR data export."""

    format: Literal["json", "csv"] = Field(default="json", description="Export format")
    include_documents: bool = Field(default=True, description="Include uploaded documents metadata")
    include_search_history: bool = Field(default=True, description="Include search history")
    include_favorites: bool = Field(default=True, description="Include favorites")


class DataExportResponse(BaseModel):
    """GDPR data export response."""

    export_id: str
    status: Literal["pending", "processing", "completed", "failed"] = "pending"
    download_url: Optional[str] = None
    expires_at: Optional[datetime] = None
    format: str
    includes: list[str]
    estimated_size_kb: Optional[int] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DataExportStatusResponse(BaseModel):
    """Schema for checking export job status."""

    export_id: str
    status: Literal["pending", "processing", "completed", "failed"]
    progress_percent: int = 0
    download_url: Optional[str] = None
    expires_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class TokenResponse(BaseModel):
    """Schema for token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request."""

    refresh_token: str


class PasswordResetRequest(BaseModel):
    """Schema for password reset request."""

    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation."""

    token: str
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v


class EmailVerificationRequest(BaseModel):
    """Schema for email verification request."""

    token: str


class ResendVerificationRequest(BaseModel):
    """Schema for resend verification email request."""

    email: EmailStr


class OAuthAuthorizeResponse(BaseModel):
    """Schema for OAuth authorization response."""

    authorization_url: str
    state: str


class OAuthCallbackRequest(BaseModel):
    """Schema for OAuth callback."""

    code: str
    state: str
    provider: str


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str
    detail: Optional[str] = None


# Saved Search Schemas
AlertFrequencyType = Literal["instant", "daily", "weekly", "none"]


class SavedSearchCreate(BaseModel):
    """Schema for creating a saved search."""

    name: str = Field(..., min_length=1, max_length=255, description="Search name")
    description: Optional[str] = Field(None, max_length=1000, description="Search description")
    filters: dict[str, Any] = Field(
        default_factory=dict,
        description="Search filters (city, min_price, max_price, etc.)",
    )
    alert_frequency: AlertFrequencyType = Field(default="daily", description="Alert frequency")
    notify_on_new: bool = Field(default=True, description="Notify on new properties")
    notify_on_price_drop: bool = Field(default=True, description="Notify on price drops")


class SavedSearchUpdate(BaseModel):
    """Schema for updating a saved search."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    filters: Optional[dict[str, Any]] = None
    alert_frequency: Optional[AlertFrequencyType] = None
    is_active: Optional[bool] = None
    notify_on_new: Optional[bool] = None
    notify_on_price_drop: Optional[bool] = None


class SavedSearchResponse(BaseModel):
    """Schema for saved search response."""

    id: str
    user_id: str
    name: str
    description: Optional[str] = None
    filters: dict[str, Any]
    alert_frequency: str
    is_active: bool
    notify_on_new: bool
    notify_on_price_drop: bool
    created_at: datetime
    updated_at: datetime
    last_used_at: Optional[datetime] = None
    use_count: int = 0

    model_config = {"from_attributes": True}


class SavedSearchListResponse(BaseModel):
    """Schema for list of saved searches."""

    items: list[SavedSearchResponse]
    total: int


# Collection Schemas
class CollectionCreate(BaseModel):
    """Schema for creating a collection."""

    name: str = Field(..., min_length=1, max_length=255, description="Collection name")
    description: Optional[str] = Field(None, max_length=1000, description="Collection description")


class CollectionUpdate(BaseModel):
    """Schema for updating a collection."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)


class CollectionResponse(BaseModel):
    """Schema for collection response."""

    id: str
    user_id: str
    name: str
    description: Optional[str] = None
    is_default: bool = False
    created_at: datetime
    updated_at: datetime
    favorite_count: int = 0  # Computed field

    model_config = {"from_attributes": True}


class CollectionListResponse(BaseModel):
    """Schema for list of collections."""

    items: list[CollectionResponse]
    total: int


# Favorite Schemas
class FavoriteCreate(BaseModel):
    """Schema for creating a favorite."""

    property_id: str = Field(..., min_length=1, max_length=255, description="Property ID")
    collection_id: Optional[str] = Field(None, description="Optional collection ID")
    notes: Optional[str] = Field(None, max_length=2000, description="User notes about property")


class FavoriteUpdate(BaseModel):
    """Schema for updating a favorite."""

    collection_id: Optional[str] = None  # None means "uncategorized"
    notes: Optional[str] = Field(None, max_length=2000)


class FavoriteResponse(BaseModel):
    """Schema for favorite response (without property data)."""

    id: str
    user_id: str
    property_id: str
    collection_id: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FavoriteWithPropertyResponse(BaseModel):
    """Schema for favorite response with full property data from ChromaDB."""

    id: str
    user_id: str
    property_id: str
    collection_id: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    property: Optional[dict[str, Any]] = None  # Full property data from ChromaDB
    is_available: bool = True  # False if property no longer exists in ChromaDB

    model_config = {"from_attributes": True}


class FavoriteListResponse(BaseModel):
    """Schema for list of favorites."""

    items: list[FavoriteWithPropertyResponse]
    total: int
    unavailable_count: int = 0  # Count of properties no longer in ChromaDB


class FavoriteCheckResponse(BaseModel):
    """Schema for checking if a property is favorited."""

    is_favorited: bool
    favorite_id: Optional[str] = None
    collection_id: Optional[str] = None
    notes: Optional[str] = None


# Price Snapshot Schemas (Task #38: Price History & Trends)
TrendDirectionType = Literal["increasing", "decreasing", "stable", "insufficient_data"]
MarketTrendType = Literal["rising", "falling", "stable"]
ConfidenceType = Literal["high", "medium", "low"]
IntervalType = Literal["month", "quarter", "year"]


class PriceSnapshotResponse(BaseModel):
    """Schema for a single price snapshot."""

    id: str
    property_id: str
    price: float
    price_per_sqm: Optional[float] = None
    currency: Optional[str] = None
    source: Optional[str] = None
    recorded_at: datetime

    model_config = {"from_attributes": True}


class PriceHistoryResponse(BaseModel):
    """Schema for property price history."""

    property_id: str
    snapshots: list[PriceSnapshotResponse]
    total: int
    current_price: Optional[float] = None
    first_recorded: Optional[datetime] = None
    last_recorded: Optional[datetime] = None
    price_change_percent: Optional[float] = None  # From first to last
    trend: TrendDirectionType


class MarketTrendPoint(BaseModel):
    """Schema for a single point in market trend data."""

    period: str  # e.g., "2024-01", "2024-Q1"
    start_date: datetime
    end_date: datetime
    average_price: float
    median_price: float
    volume: int
    avg_price_per_sqm: Optional[float] = None
    # The currency the prices of this period are in - the interface quotes
    # them in it instead of assuming dollars.
    currency: Optional[str] = None


class MarketTrendsResponse(BaseModel):
    """Schema for market trend data."""

    city: Optional[str] = None
    district: Optional[str] = None
    interval: IntervalType
    data_points: list[MarketTrendPoint]
    trend_direction: TrendDirectionType
    change_percent: Optional[float] = None
    confidence: ConfidenceType


class MarketIndicatorsResponse(BaseModel):
    """Schema for market indicators."""

    city: Optional[str] = None
    overall_trend: MarketTrendType
    avg_price_change_1m: Optional[float] = None
    avg_price_change_3m: Optional[float] = None
    avg_price_change_6m: Optional[float] = None
    avg_price_change_1y: Optional[float] = None
    total_listings: int
    new_listings_7d: int
    price_drops_7d: int
    hottest_districts: list[dict[str, Any]]  # Top 5 districts by activity
    coldest_districts: list[dict[str, Any]]  # Bottom 5 districts


class AreaInsightsResponse(BaseModel):
    """Schema for insights about a single area/city."""

    city: str
    property_count: int
    avg_price: float
    median_price: float
    avg_price_per_sqm: Optional[float] = None
    most_common_room_count: Optional[float] = None
    amenity_availability: dict[str, float] = Field(default_factory=dict)
    price_comparison: Optional[str] = None  # "above_average", "below_average", "average"


class AreaComparisonResponse(BaseModel):
    """Schema for comparing two areas side by side."""

    area1: AreaInsightsResponse
    area2: AreaInsightsResponse
    price_difference: float
    price_difference_percent: float
    cheaper_area: str
    more_properties_area: str
    comparison_timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


# = Anomaly-related schemas =
AnomalyType = Literal["price_spike", "price_drop", "volume_spike", "volume_drop", "unusual_pattern"]
AnomalySeverity = Literal["low", "medium", "high", "critical"]
AnomalyScope = Literal["property", "city", "district", "market", "region"]


class AnomalyBase(BaseModel):
    """Base schema for anomaly data."""

    id: str
    anomaly_type: AnomalyType  # type: ignore
    severity: AnomalySeverity  # type: ignore
    scope_type: AnomalyScope  # type: ignore
    scope_id: str
    detected_at: datetime
    algorithm: str
    threshold_used: float
    metric_name: str
    expected_value: float
    actual_value: float
    deviation_percent: float
    z_score: Optional[float] = None
    alert_sent: bool = False
    alert_sent_at: Optional[datetime] = None
    dismissed_by: Optional[str] = None
    dismissed_at: Optional[datetime] = None
    context: dict[str, Any] = Field(default_factory=dict)

    model_config = {"from_attributes": True}


class AnomalyResponse(AnomalyBase):
    """Schema for anomaly response - includes all fields from AnomalyBase."""

    pass


class AnomalyListResponse(BaseModel):
    """Schema for list of anomalies."""

    anomalies: list[AnomalyResponse]
    total: int
    limit: int
    offset: int


class AnomalyStatsResponse(BaseModel):
    """Schema for anomaly statistics."""

    total: int
    by_severity: dict[str, int]
    by_type: dict[str, int]
    undismissed: int


class AnomalyDismissRequest(BaseModel):
    """Schema for dismissing an anomaly."""

    dismissed_by: Optional[str] = None
    reason: Optional[str] = None

    model_config = {"from_attributes": True}


# =============================================================================
# Lead Scoring System Schemas (Task #55)
# =============================================================================

LeadStatusType = Literal["new", "contacted", "qualified", "converted", "lost"]
LeadSourceType = Literal[
    "organic", "referral", "ads", "direct", "email", "social", "propvector_waitlist"
]
InteractionType = Literal[
    "search",
    "view",
    "favorite",
    "unfavorite",
    "inquiry",
    "contact",
    "schedule_viewing",
    "share",
    "save_search",
    "download_report",
    "navigation",
]


# = Lead Schemas =


class LeadCreate(BaseModel):
    """Schema for creating a new lead (usually from tracking)."""

    visitor_id: str = Field(
        ..., min_length=1, max_length=36, description="Visitor UUID from cookie"
    )
    user_id: Optional[str] = Field(None, description="Linked user ID if registered")
    email: Optional[EmailStr] = Field(None, description="Lead email address")
    phone: Optional[str] = Field(None, max_length=50, description="Lead phone number")
    name: Optional[str] = Field(None, max_length=255, description="Lead name")
    source: Optional[LeadSourceType] = Field(None, description="Lead source")
    consent_given: bool = Field(default=False, description="GDPR consent status")


class LeadUpdate(BaseModel):
    """Schema for updating lead information."""

    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    name: Optional[str] = Field(None, max_length=255)
    budget_min: Optional[float] = Field(None, ge=0)
    budget_max: Optional[float] = Field(None, ge=0)
    preferred_locations: Optional[list[str]] = None
    status: Optional[LeadStatusType] = None
    consent_given: Optional[bool] = None


class LeadResponse(BaseModel):
    """Schema for lead response."""

    id: str
    visitor_id: str
    user_id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    name: Optional[str] = None
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    preferred_locations: Optional[list[str]] = None
    status: str
    source: Optional[str] = None
    current_score: int
    first_seen_at: datetime
    last_activity_at: datetime
    created_at: datetime
    updated_at: datetime
    consent_given: bool
    consent_at: Optional[datetime] = None

    # Computed fields
    assigned_agent_id: Optional[str] = None
    assigned_agent_name: Optional[str] = None

    model_config = {"from_attributes": True}


class LeadWithScoreResponse(LeadResponse):
    """Schema for lead response with latest score breakdown."""

    latest_score: Optional["LeadScoreResponse"] = None
    interaction_count: int = 0
    # The prioritized breakdown that `POST /leads` computes. The endpoint has
    # always passed this value, but the model never declared the field, so
    # pydantic (extra='ignore') dropped it and the client received a lead with
    # no priority score — while the endpoint's own summary promised one.
    # Declared here so the response matches what the endpoint advertises.
    priority_score: Optional["PrioritizedScoreResponse"] = None


class LeadListResponse(BaseModel):
    """Schema for paginated list of leads."""

    items: list[LeadWithScoreResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class LeadDetailResponse(LeadWithScoreResponse):
    """Schema for detailed lead response with interactions."""

    recent_interactions: list["LeadInteractionResponse"] = []
    score_history: list["LeadScoreResponse"] = []


# = Lead Interaction Schemas =


class CityCount(BaseModel):
    """How many properties a city holds."""

    name: str = Field(..., description="City name")
    count: int = Field(0, ge=0, description="Properties in the city")


class CatalogueStatsResponse(BaseModel):
    """What the catalogue holds - the numbers the landing page shows."""

    total: int = Field(0, ge=0, description="Properties in the catalogue")
    agents: int = Field(0, ge=0, description="Agents in the catalogue")
    cities: list[CityCount] = Field(default_factory=list, description="Properties per city")
    currencies: list[str] = Field(default_factory=list, description="Currencies in the catalogue")


class OutboundClickRequest(BaseModel):
    """A click that leaves the site."""

    target: str = Field(..., min_length=1, max_length=200, description="Where the click went")
    slot: Optional[str] = Field(None, max_length=200, description="The slot on the page")
    campaign: Optional[str] = Field(None, max_length=100, description="The campaign it belongs to")
    visitor_id: str = Field(
        "anonymous", min_length=1, max_length=36, description="Visitor UUID from the cookie"
    )
    page_url: Optional[str] = Field(None, max_length=500, description="The page it happened on")


class TrackInteractionRequest(BaseModel):
    """Schema for tracking a lead interaction."""

    visitor_id: str = Field(
        ..., min_length=1, max_length=36, description="Visitor UUID from cookie"
    )
    interaction_type: InteractionType = Field(..., description="Type of interaction")
    property_id: Optional[str] = Field(
        None, max_length=255, description="Property ID if applicable"
    )
    search_query: Optional[str] = Field(None, max_length=1000, description="Search query if search")
    metadata: Optional[dict[str, Any]] = Field(None, description="Additional context")
    session_id: Optional[str] = Field(None, max_length=36, description="Session ID")
    page_url: Optional[str] = Field(None, max_length=500, description="Current page URL")
    referrer: Optional[str] = Field(None, max_length=500, description="Referrer URL")
    time_spent_seconds: Optional[int] = Field(None, ge=0, description="Time on page")


class LeadInteractionResponse(BaseModel):
    """Schema for lead interaction response."""

    id: str
    lead_id: str
    interaction_type: str
    property_id: Optional[str] = None
    search_query: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None
    session_id: Optional[str] = None
    page_url: Optional[str] = None
    time_spent_seconds: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class LeadInteractionListResponse(BaseModel):
    """Schema for paginated list of interactions."""

    items: list[LeadInteractionResponse]
    total: int
    page: int
    page_size: int


# = Lead Score Schemas =


class LeadScoreResponse(BaseModel):
    """Schema for lead score response with breakdown."""

    id: str
    lead_id: str
    total_score: int = Field(..., ge=0, le=100, description="Total score 0-100")
    search_activity_score: int = Field(..., ge=0, le=100)
    engagement_score: int = Field(..., ge=0, le=100)
    intent_score: int = Field(..., ge=0, le=100)
    score_factors: dict[str, Any] = Field(default_factory=dict)
    recommendations: Optional[list[str]] = None
    model_version: str
    calculated_at: datetime

    model_config = {"from_attributes": True}


class LeadScoreBreakdown(BaseModel):
    """Schema for detailed score breakdown explanation."""

    total_score: int
    components: dict[str, int] = Field(
        ...,
        description="Component scores: search_activity, engagement, intent",
    )
    factors: dict[str, Any] = Field(
        ...,
        description="Raw factors: search_count, view_count, favorite_count, etc.",
    )
    weights: dict[str, float] = Field(
        ...,
        description="Weights used for each component",
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="AI-generated recommendations",
    )
    percentile: Optional[float] = Field(
        None,
        description="Percentile rank among all leads",
    )


# = Agent Assignment Schemas =


class AgentAssignmentCreate(BaseModel):
    """Schema for assigning an agent to a lead."""

    agent_id: str = Field(..., description="User ID of the agent")
    notes: Optional[str] = Field(None, max_length=2000, description="Assignment notes")
    is_primary: bool = Field(default=False, description="Is this the primary agent?")


class AgentAssignmentUpdate(BaseModel):
    """Schema for updating an assignment."""

    notes: Optional[str] = Field(None, max_length=2000)
    is_primary: Optional[bool] = None
    is_active: Optional[bool] = None


class AgentAssignmentResponse(BaseModel):
    """Schema for agent assignment response."""

    id: str
    lead_id: str
    agent_id: str
    agent_name: Optional[str] = None
    agent_email: Optional[str] = None
    assigned_at: datetime
    assigned_by: Optional[str] = None
    notes: Optional[str] = None
    is_primary: bool
    is_active: bool

    model_config = {"from_attributes": True}


# = Lead Filters and Query Schemas =


class LeadFilters(BaseModel):
    """Schema for filtering leads."""

    status: Optional[LeadStatusType] = None
    score_min: Optional[int] = Field(None, ge=0, le=100)
    score_max: Optional[int] = Field(None, ge=0, le=100)
    source: Optional[LeadSourceType] = None
    assigned_agent_id: Optional[str] = None
    has_email: Optional[bool] = None
    has_phone: Optional[bool] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    last_activity_after: Optional[datetime] = None
    search_query: Optional[str] = Field(None, max_length=255, description="Search in name/email")


class LeadSortOptions(BaseModel):
    """Schema for sorting leads."""

    sort_by: Literal["score", "last_activity", "created_at", "name"] = "score"
    sort_order: Literal["asc", "desc"] = "desc"


# = Bulk Operations Schemas =


class BulkAssignRequest(BaseModel):
    """Schema for bulk assigning leads to an agent."""

    lead_ids: list[str] = Field(..., min_length=1, max_length=100)
    agent_id: str
    notes: Optional[str] = None


class BulkStatusUpdateRequest(BaseModel):
    """Schema for bulk updating lead status."""

    lead_ids: list[str] = Field(..., min_length=1, max_length=100)
    status: LeadStatusType


class BulkOperationResponse(BaseModel):
    """Schema for bulk operation response."""

    success_count: int
    failed_count: int
    failed_ids: Optional[list[str]] = None
    message: str


# = Export Schemas =


class LeadExportRequest(BaseModel):
    """Schema for exporting leads."""

    filters: Optional[LeadFilters] = None
    format: Literal["csv", "json"] = "csv"
    include_interactions: bool = False
    include_scores: bool = True


class LeadExportResponse(BaseModel):
    """Schema for export response."""

    download_url: str
    expires_at: datetime
    total_records: int
    format: str


# = Recalculate Scores Schema =


class RecalculateScoresRequest(BaseModel):
    """Schema for triggering score recalculation."""

    lead_ids: Optional[list[str]] = Field(
        None,
        description="Specific lead IDs to recalculate. If None, recalculate all.",
    )
    force: bool = Field(
        default=False,
        description="Force recalculation even if recently calculated",
    )


class RecalculateScoresResponse(BaseModel):
    """Schema for recalculation response."""

    recalculated_count: int
    failed_count: int
    duration_seconds: float
    message: str


# =============================================================================
# Agent Performance Analytics Schemas (Task #56)
# =============================================================================

# Type literals
DealStatusType = Literal[
    "offer_submitted", "offer_accepted", "contract_signed", "closed", "fell_through"
]
DealTypeType = Literal["sale", "rent"]
CommissionStatusType = Literal["pending", "approved", "paid", "clawed_back"]
CommissionTypeType = Literal["primary", "split", "referral"]
GoalTypeType = Literal["leads", "deals", "revenue", "gci"]
PeriodTypeType = Literal["daily", "weekly", "monthly", "quarterly", "yearly"]


# Deal Schemas
class DealCreate(BaseModel):
    """Schema for creating a deal."""

    lead_id: str
    property_id: Optional[str] = None
    deal_type: DealTypeType
    deal_value: float = Field(..., ge=0)
    property_type: Optional[str] = None
    property_city: Optional[str] = None
    property_district: Optional[str] = None
    notes: Optional[str] = None


class DealUpdate(BaseModel):
    """Schema for updating a deal."""

    status: Optional[DealStatusType] = None
    deal_value: Optional[float] = Field(None, ge=0)
    notes: Optional[str] = None
    offer_accepted_at: Optional[datetime] = None
    contract_signed_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None


class DealResponse(BaseModel):
    """Schema for deal response."""

    id: str
    lead_id: str
    agent_id: str
    property_id: Optional[str] = None
    deal_type: str
    deal_value: float
    currency: str
    status: str
    property_type: Optional[str] = None
    property_city: Optional[str] = None
    property_district: Optional[str] = None
    offer_submitted_at: datetime
    offer_accepted_at: Optional[datetime] = None
    contract_signed_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    days_to_close: Optional[int] = None  # Calculated field
    created_at: datetime

    model_config = {"from_attributes": True}


class DealListResponse(BaseModel):
    """Schema for paginated list of deals."""

    items: list[DealResponse]
    total: int
    page: int
    page_size: int


# Commission Schemas
class CommissionCreate(BaseModel):
    """Schema for creating a commission."""

    agent_id: str
    commission_type: CommissionTypeType = "primary"
    commission_rate: float = Field(..., ge=0, le=1)  # 0-1 range (e.g., 0.03 for 3%)
    notes: Optional[str] = None


class CommissionResponse(BaseModel):
    """Schema for commission response."""

    id: str
    deal_id: str
    agent_id: str
    commission_type: str
    commission_rate: float
    commission_amount: float
    status: str
    paid_at: Optional[datetime] = None
    payment_reference: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# Agent Metrics Schemas
class AgentMetricsResponse(BaseModel):
    """Schema for agent performance metrics."""

    # Lead metrics
    total_leads: int
    active_leads: int
    new_leads_week: int
    high_value_leads: int  # Score >= 70

    # Deal metrics
    total_deals: int
    active_deals: int
    closed_deals: int
    fell_through_deals: int

    # Conversion metrics
    lead_to_qualified_rate: float  # percentage 0-100
    qualified_to_deal_rate: float
    overall_conversion_rate: float

    # Time metrics
    avg_time_to_first_contact_hours: Optional[float] = None
    avg_time_to_qualify_days: Optional[float] = None
    avg_time_to_close_days: Optional[float] = None

    # Financial metrics
    total_deal_value: float
    avg_deal_value: float
    total_commission: float
    pending_commission: float

    # Strengths analysis
    top_property_types: list[dict[str, Any]]
    top_locations: list[dict[str, Any]]
    avg_lead_score: float

    # Period comparison
    deals_change_percent: Optional[float] = None
    revenue_change_percent: Optional[float] = None


class TeamComparisonResponse(BaseModel):
    """Schema for team comparison data."""

    agent_id: str
    agent_name: str

    # Rank in team
    rank_by_deals: int
    rank_by_revenue: int
    rank_by_conversion: int
    total_agents: int

    # Comparison to average (percentage difference)
    deals_vs_avg_percent: float  # e.g., +15.5 means 15.5% above average
    revenue_vs_avg_percent: float
    conversion_vs_avg_percent: float
    time_to_close_vs_avg_percent: float

    # Team averages
    team_avg_deals: float
    team_avg_revenue: float
    team_avg_conversion: float
    team_avg_time_to_close_days: float


class PerformanceTrendPoint(BaseModel):
    """Schema for a single performance trend data point."""

    period: str  # "2024-01", "2024-W05", etc.
    period_start: datetime
    period_end: datetime
    leads: int
    deals_closed: int
    revenue: float
    conversion_rate: float
    avg_deal_value: float


class PerformanceTrendsResponse(BaseModel):
    """Schema for performance trends over time."""

    trends: list[PerformanceTrendPoint]
    interval: str  # day, week, month, quarter


class CoachingInsightResponse(BaseModel):
    """Schema for a coaching insight."""

    category: str  # strength, improvement, opportunity
    title: str
    description: str
    actionable_recommendation: str
    priority: int  # 1-5, 1 being highest


class CoachingInsightsResponse(BaseModel):
    """Schema for coaching insights."""

    insights: list[CoachingInsightResponse]


class GoalProgressResponse(BaseModel):
    """Schema for a single goal progress."""

    id: str
    goal_type: str
    target_value: float
    current_value: float
    progress_percent: float
    period_type: str
    period_start: datetime
    period_end: datetime
    is_achieved: bool
    days_remaining: int

    model_config = {"from_attributes": True}


class GoalProgressListResponse(BaseModel):
    """Schema for goal progress list."""

    goals: list[GoalProgressResponse]


class TopPerformerEntry(BaseModel):
    """Schema for a top performer entry."""

    agent_id: str
    agent_name: str
    agent_email: Optional[str] = None
    metric_value: float
    rank: int


class TopPerformersResponse(BaseModel):
    """Schema for top performers list."""

    performers: list[TopPerformerEntry]
    metric: str  # deals, revenue, conversion
    period_days: int


class AgentNeedingSupport(BaseModel):
    """Schema for an agent flagged as needing support."""

    agent_id: str
    agent_name: str
    agent_email: Optional[str] = None
    days_without_deal: int
    total_leads: int
    conversion_rate: float
    last_deal_at: Optional[datetime] = None
    suggested_actions: list[str]


class AgentsNeedingSupportResponse(BaseModel):
    """Schema for agents needing support list."""

    agents: list[AgentNeedingSupport]
    threshold_days: int


# Goal Management Schemas
class AgentGoalCreate(BaseModel):
    """Schema for creating an agent goal."""

    goal_type: GoalTypeType
    target_value: float = Field(..., gt=0)
    period_type: PeriodTypeType
    period_start: datetime
    period_end: datetime


class AgentGoalUpdate(BaseModel):
    """Schema for updating an agent goal."""

    target_value: Optional[float] = Field(None, gt=0)
    current_value: Optional[float] = None
    is_active: Optional[bool] = None


# Resolve forward references
# Neither model is rebuilt here. LeadWithScoreResponse forward-references
# PrioritizedScoreResponse, which is defined much further down this module, and
# LeadDetailResponse inherits from LeadWithScoreResponse — so rebuilding either
# one here raises PydanticUndefinedAnnotation (a name that does not exist yet)
# and takes the whole module import down with it. Both rebuilds live at the end
# of the file, after every referenced class exists.


# =============================================================================
# Push Notification Schemas (Task #63)
# =============================================================================


class PushSubscriptionCreate(BaseModel):
    """Schema for creating a push subscription."""

    endpoint: str = Field(..., max_length=500, description="Push subscription endpoint URL")
    keys: dict[str, str] = Field(..., description="VAPID keys with p256dh and auth")


class PushSubscriptionResponse(BaseModel):
    """Schema for push subscription response."""

    id: str
    endpoint: str
    is_active: bool
    device_name: Optional[str] = None
    created_at: datetime
    last_used_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PushSubscriptionListResponse(BaseModel):
    """Schema for list of push subscriptions."""

    items: list[PushSubscriptionResponse]
    total: int


class VapidPublicKeyResponse(BaseModel):
    """Schema for VAPID public key response."""

    public_key: str
    enabled: bool


class PushNotificationSend(BaseModel):
    """Schema for sending a push notification (internal use)."""

    title: str = Field(..., max_length=100)
    body: str = Field(..., max_length=500)
    icon: Optional[str] = Field(None, max_length=500)
    data: Optional[dict[str, Any]] = None


# =============================================================================
# Agent/Broker System Schemas (Task #45)
# =============================================================================

# Type literals
InquiryStatusType = Literal["new", "read", "responded", "closed"]
InquiryTypeType = Literal["general", "property", "financing", "viewing"]
AppointmentStatusType = Literal["requested", "confirmed", "cancelled", "completed"]
ListingTypeType = Literal["sale", "rent", "both"]


# Agent Profile Schemas
class AgentProfileCreate(BaseModel):
    """Schema for creating an agent profile."""

    agency_name: Optional[str] = Field(None, max_length=255)
    agency_id: Optional[str] = Field(None, max_length=36)
    license_number: Optional[str] = Field(None, max_length=100)
    license_state: Optional[str] = Field(None, max_length=50)
    professional_email: Optional[EmailStr] = None
    professional_phone: Optional[str] = Field(None, max_length=50)
    office_address: Optional[str] = Field(None, max_length=500)
    specialties: Optional[list[str]] = None
    service_areas: Optional[list[str]] = None
    property_types: Optional[list[str]] = None
    languages: Optional[list[str]] = None
    bio: Optional[str] = Field(None, max_length=2000)
    profile_image_url: Optional[str] = Field(None, max_length=500)


class AgentProfileUpdate(BaseModel):
    """Schema for updating an agent profile."""

    agency_name: Optional[str] = Field(None, max_length=255)
    license_number: Optional[str] = Field(None, max_length=100)
    license_state: Optional[str] = Field(None, max_length=50)
    professional_email: Optional[EmailStr] = None
    professional_phone: Optional[str] = Field(None, max_length=50)
    office_address: Optional[str] = Field(None, max_length=500)
    specialties: Optional[list[str]] = None
    service_areas: Optional[list[str]] = None
    property_types: Optional[list[str]] = None
    languages: Optional[list[str]] = None
    bio: Optional[str] = Field(None, max_length=2000)
    profile_image_url: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None


class AgentProfileResponse(BaseModel):
    """Schema for agent profile response."""

    id: str
    user_id: str
    # User info (joined)
    name: Optional[str] = None
    email: Optional[str] = None
    # Professional info
    agency_name: Optional[str] = None
    license_number: Optional[str] = None
    license_state: Optional[str] = None
    professional_email: Optional[str] = None
    professional_phone: Optional[str] = None
    office_address: Optional[str] = None
    # Specialization
    specialties: Optional[list[str]] = None
    service_areas: Optional[list[str]] = None
    property_types: Optional[list[str]] = None
    languages: Optional[list[str]] = None
    # Rating & Stats
    average_rating: float
    total_reviews: int
    total_sales: int
    total_rentals: int
    # Status
    is_verified: bool
    is_active: bool
    # Media
    profile_image_url: Optional[str] = None
    bio: Optional[str] = None
    # Timestamps
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AgentProfileListResponse(BaseModel):
    """Schema for paginated list of agent profiles."""

    items: list[AgentProfileResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class AgentFilters(BaseModel):
    """Schema for filtering agents."""

    city: Optional[str] = Field(None, max_length=100)
    specialty: Optional[str] = Field(None, max_length=50)
    property_type: Optional[str] = Field(None, max_length=50)
    min_rating: Optional[float] = Field(None, ge=0, le=5)
    agency_id: Optional[str] = None
    is_verified: Optional[bool] = None
    language: Optional[str] = Field(None, max_length=10)
    sort_by: Literal["rating", "listings", "reviews", "created"] = "rating"
    sort_order: Literal["asc", "desc"] = "desc"


# Agent Listing Schemas
class AgentListingCreate(BaseModel):
    """Schema for creating an agent listing."""

    property_id: str = Field(..., max_length=255)
    listing_type: ListingTypeType = "sale"
    is_primary: bool = False
    commission_rate: Optional[float] = Field(None, ge=0, le=1)


class AgentListingResponse(BaseModel):
    """Schema for agent listing response."""

    id: str
    agent_id: str
    property_id: str
    listing_type: str
    is_primary: bool
    is_active: bool
    commission_rate: Optional[float] = None
    created_at: datetime
    # Optional property data (from ChromaDB)
    property: Optional[dict[str, Any]] = None

    model_config = {"from_attributes": True}


class AgentListingListResponse(BaseModel):
    """Schema for list of agent listings."""

    items: list[AgentListingResponse]
    total: int


# Agent Inquiry Schemas
class AgentInquiryCreate(BaseModel):
    """Schema for creating an agent inquiry (contact form)."""

    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=50)
    property_id: Optional[str] = Field(None, max_length=255)
    inquiry_type: InquiryTypeType = "general"
    message: str = Field(..., min_length=10, max_length=5000)


class AgentInquiryUpdate(BaseModel):
    """Schema for updating an inquiry (agent only)."""

    status: Optional[InquiryStatusType] = None
    notes: Optional[str] = Field(None, max_length=2000)


class AgentInquiryResponse(BaseModel):
    """Schema for agent inquiry response."""

    id: str
    agent_id: str
    # Inquirer info
    user_id: Optional[str] = None
    visitor_id: Optional[str] = None
    name: str
    email: str
    phone: Optional[str] = None
    # Inquiry details
    property_id: Optional[str] = None
    inquiry_type: str
    message: str
    # Status
    status: str
    # Timestamps
    created_at: datetime
    read_at: Optional[datetime] = None
    responded_at: Optional[datetime] = None
    # Optional property data
    property: Optional[dict[str, Any]] = None

    model_config = {"from_attributes": True}


class AgentInquiryListResponse(BaseModel):
    """Schema for paginated list of agent inquiries."""

    items: list[AgentInquiryResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# Viewing Appointment Schemas
class ViewingAppointmentCreate(BaseModel):
    """Schema for creating a viewing appointment request."""

    property_id: str = Field(..., max_length=255)
    proposed_datetime: datetime
    duration_minutes: int = Field(default=60, ge=15, le=480)  # 15 min to 8 hours
    client_name: str = Field(..., min_length=1, max_length=255)
    client_email: EmailStr
    client_phone: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = Field(None, max_length=2000)


class ViewingAppointmentUpdate(BaseModel):
    """Schema for updating an appointment (agent only)."""

    status: Optional[AppointmentStatusType] = None
    confirmed_datetime: Optional[datetime] = None
    notes: Optional[str] = Field(None, max_length=2000)
    cancellation_reason: Optional[str] = Field(None, max_length=1000)


class ViewingAppointmentResponse(BaseModel):
    """Schema for viewing appointment response."""

    id: str
    agent_id: str
    # Client info
    user_id: Optional[str] = None
    visitor_id: Optional[str] = None
    client_name: str
    client_email: str
    client_phone: Optional[str] = None
    # Property
    property_id: str
    # Scheduling
    proposed_datetime: datetime
    confirmed_datetime: Optional[datetime] = None
    duration_minutes: int
    # Status
    status: str
    notes: Optional[str] = None
    cancellation_reason: Optional[str] = None
    # Timestamps
    created_at: datetime
    updated_at: datetime
    # Optional property data
    property: Optional[dict[str, Any]] = None
    # Optional agent info
    agent_name: Optional[str] = None

    model_config = {"from_attributes": True}


class ViewingAppointmentListResponse(BaseModel):
    """Schema for paginated list of viewing appointments."""

    items: list[ViewingAppointmentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# =============================================================================
# Document Management Schemas (Task #43)
# =============================================================================

# Type literals
DocumentCategoryType = Literal["contract", "inspection", "photo", "financial", "other"]
OCRStatusType = Literal["pending", "processing", "completed", "failed"]


class DocumentCreate(BaseModel):
    """Schema for document upload metadata."""

    property_id: Optional[str] = Field(None, max_length=255, description="Associated property ID")
    category: Optional[DocumentCategoryType] = Field(None, description="Document category")
    tags: Optional[list[str]] = Field(None, description="Tags for organization")
    description: Optional[str] = Field(None, max_length=2000, description="Document description")
    expiry_date: Optional[datetime] = Field(None, description="Document expiry date")


class DocumentUpdate(BaseModel):
    """Schema for updating document metadata."""

    property_id: Optional[str] = Field(None, max_length=255)
    category: Optional[DocumentCategoryType] = None
    tags: Optional[list[str]] = None
    description: Optional[str] = Field(None, max_length=2000)
    expiry_date: Optional[datetime] = None


class DocumentResponse(BaseModel):
    """Schema for document response."""

    id: str
    user_id: str
    property_id: Optional[str] = None
    filename: str  # Unique stored filename
    original_filename: str  # Original upload name
    file_type: str  # MIME type
    file_size: int  # Size in bytes
    category: Optional[str] = None
    tags: Optional[list[str]] = None
    description: Optional[str] = None
    expiry_date: Optional[datetime] = None
    ocr_status: str  # pending, processing, completed, failed
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentWithTextResponse(DocumentResponse):
    """Schema for document response with extracted text."""

    extracted_text: Optional[str] = None


class DocumentListResponse(BaseModel):
    """Schema for paginated list of documents."""

    items: list[DocumentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ExpiringDocumentsResponse(BaseModel):
    """Schema for expiring documents response."""

    items: list[DocumentResponse]
    total: int
    days_ahead: int


class DocumentUploadResponse(BaseModel):
    """Schema for document upload response."""

    id: str
    filename: str
    original_filename: str
    file_type: str
    file_size: int
    message: str


class DocumentFilters(BaseModel):
    """Schema for filtering documents."""

    property_id: Optional[str] = Field(None, max_length=255)
    category: Optional[DocumentCategoryType] = None
    tags: Optional[list[str]] = None
    ocr_status: Optional[OCRStatusType] = None
    has_expiry: Optional[bool] = None
    expiry_before: Optional[datetime] = None
    expiry_after: Optional[datetime] = None
    search_query: Optional[str] = Field(
        None, max_length=255, description="Search in filename/description"
    )
    sort_by: Literal["created_at", "updated_at", "filename", "file_size", "expiry_date"] = (
        "created_at"
    )
    sort_order: Literal["asc", "desc"] = "desc"


# =============================================================================
# E-Signature Schemas
# =============================================================================

# Enums
TemplateTypeType = Literal["rental_agreement", "purchase_offer", "lease_renewal", "custom"]
TemplateCategoryType = Literal[
    "rental",
    "purchase",
    "lease",
    "custom",
    "default",
    "user_created",
    "system",
    "shared",
    "builtin",
]
ESignatureProviderType = Literal["hellosign", "docusign"]
SignatureRequestStatusType = Literal[
    "draft", "sent", "viewed", "partially_signed", "completed", "expired", "cancelled", "declined"
]
SignerStatusType = Literal["pending", "viewed", "signed", "declined"]
SignerRoleType = Literal["landlord", "tenant", "buyer", "seller", "agent", "witness", "other"]


class SignerBase(BaseModel):
    """Base schema for signer information."""

    email: EmailStr = Field(..., description="Signer email address")
    name: str = Field(..., min_length=1, max_length=255, description="Signer full name")
    role: SignerRoleType = Field("other", description="Role of the signer")
    order: int = Field(1, ge=1, description="Signing order (1-indexed)")


class SignerCreate(SignerBase):
    """Schema for creating a signer."""

    pass


class SignerResponse(SignerBase):
    """Schema for signer response with status."""

    status: SignerStatusType = Field("pending", description="Current status")
    signed_at: Optional[datetime] = Field(None, description="When signed")
    provider_signer_id: Optional[str] = Field(None, description="Provider signer ID")
    signature_url: Optional[str] = Field(None, description="URL for signer to sign")


class DocumentTemplateResponse(BaseModel):
    """Schema for document template response."""

    id: str
    user_id: str
    name: str
    description: Optional[str] = None
    template_type: TemplateTypeType
    content: str
    variables: Optional[dict[str, Any]] = None
    is_default: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentTemplateCreate(BaseModel):
    """Schema for creating a document template."""

    name: str = Field(..., min_length=1, max_length=255, description="Template name")
    template_type: TemplateTypeType = Field(..., description="Type of template")
    description: Optional[str] = Field(None, max_length=500, description="Template description")
    content: str = Field(..., description="Jinja2 HTML template content")
    variables: Optional[dict[str, Any]] = Field(None, description="Variable definitions")
    is_default: bool = False
    category: Optional[TemplateCategoryType] = None
    tags: Optional[list[str]] = None
    expiry_date: Optional[datetime] = None


class DocumentTemplateUpdate(BaseModel):
    """Schema for updating a document template."""

    name: Optional[str] = Field(None, max_length=255, description="Template name")
    description: Optional[str] = Field(None, max_length=500, description="Template description")
    content: Optional[str] = Field(None, description="Jinja2 HTML template content")
    variables: Optional[dict[str, Any]] = Field(None, description="Variable definitions")
    is_default: Optional[bool] = Field(None, description="Set as default template")
    category: Optional[TemplateCategoryType] = None
    tags: Optional[list[str]] = None
    expiry_date: Optional[datetime] = None


class DocumentTemplateListResponse(BaseModel):
    """Schema for paginated list of document templates."""

    items: list[DocumentTemplateResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class SignatureRequestCreate(BaseModel):
    """Schema for creating a signature request."""

    title: str = Field(
        ..., min_length=1, max_length=255, description="Title of the document to sign"
    )
    template_id: Optional[str] = Field(None, description="Template ID to use")
    document_id: Optional[str] = Field(None, description="Existing document ID to sign")
    subject: Optional[str] = Field(None, max_length=255, description="Email subject")
    message: Optional[str] = Field(None, max_length=2000, description="Email message to signers")
    signers: list[SignerCreate] = Field(
        ..., min_length=1, max_length=10, description="List of signers"
    )
    variables: Optional[dict[str, Any]] = Field(None, description="Template variables to fill")
    property_id: Optional[str] = Field(None, description="Associated property ID")
    expires_in_days: Optional[int] = Field(None, ge=1, le=365, description="Days until expiry")
    provider: Optional[ESignatureProviderType] = Field(
        "hellosign", description="E-signature provider to use"
    )

    @field_validator("signers")
    @classmethod
    def validate_signers(cls, v: list[SignerCreate]) -> list[SignerCreate]:
        if len(v) == 0:
            raise ValueError("At least one signer is required")
        if len(v) > 10:
            raise ValueError("Maximum 10 signers allowed")
        return v


class SignatureRequestResponse(BaseModel):
    """Schema for signature request response."""

    id: str
    user_id: str
    title: str
    subject: Optional[str] = None
    message: Optional[str] = None
    document_id: Optional[str] = None
    template_id: Optional[str] = None
    property_id: Optional[str] = None
    provider: ESignatureProviderType
    provider_envelope_id: Optional[str] = None
    signers: list[SignerResponse]
    status: SignatureRequestStatusType
    created_at: datetime
    sent_at: Optional[datetime] = None
    viewed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    reminder_count: int = 0

    model_config = {"from_attributes": True}


class SignatureRequestListResponse(BaseModel):
    """Schema for paginated list of signature requests."""

    items: list[SignatureRequestResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class SignatureRequestFilters(BaseModel):
    """Schema for filtering signature requests."""

    status: Optional[SignatureRequestStatusType] = None
    property_id: Optional[str] = Field(None, description="Filter by property ID")
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Page size")

    sort_by: Literal["created_at", "updated_at", "title", "status"] = Field(
        "created_at", description="Sort field"
    )
    sort_order: Literal["asc", "desc"] = Field("desc", description="Sort order")


# =============================================================================
# Signed Document Schemas
# =============================================================================


class SignedDocumentResponse(BaseModel):
    """Schema for signed document response."""

    id: str
    signature_request_id: str
    document_id: Optional[str] = None
    storage_path: str
    file_size: int
    provider_document_id: Optional[str] = None
    certificate_url: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# =============================================================================
# Webhook Schemas (for HelloSign callbacks)
# =============================================================================


class HelloSignWebhookEvent(str, Enum):
    """HelloSign webhook event types."""

    signature_request_sent = "signature_request_sent"
    signature_request_viewed = "signature_request_viewed"
    signature_request_signed = "signature_request_signed"
    signature_request_declined = "signature_request_declined"
    signature_request_canceled = "signature_request_canceled"


class HelloSignWebhookPayload(BaseModel):
    """Schema for HelloSign webhook payload."""

    event: HelloSignWebhookEvent
    signature_request: dict
    signature_request_id: Optional[str] = None  # Internal ID if provided in metadata
    timestamp: Optional[datetime] = None


# =============================================================================
# Filter Preset Schemas (Task #75: Advanced Filter Presets)
# =============================================================================


class FilterPresetCreate(BaseModel):
    """Schema for creating a filter preset."""

    name: str = Field(..., min_length=1, max_length=255, description="Preset name")
    description: Optional[str] = Field(None, max_length=1000, description="Preset description")
    filters: dict[str, Any] = Field(
        default_factory=dict,
        description="Filter configuration (city, min_price, max_price, rooms, etc.)",
    )
    is_default: bool = Field(default=False, description="Set as default preset")


class FilterPresetUpdate(BaseModel):
    """Schema for updating a filter preset."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    filters: Optional[dict[str, Any]] = None
    is_default: Optional[bool] = None


class FilterPresetResponse(BaseModel):
    """Schema for filter preset response."""

    id: str
    user_id: str
    name: str
    description: Optional[str] = None
    filters: dict[str, Any]
    is_default: bool
    last_used_at: Optional[datetime] = None
    use_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FilterPresetListResponse(BaseModel):
    """Schema for paginated list of filter presets."""

    items: list[FilterPresetResponse]
    total: int


# =============================================================================
# User Activity Analytics Schemas (Task #82)
# =============================================================================


class UserActivityEventType(str, Enum):
    """Types of user activity events."""

    SEARCH_QUERY = "search_query"
    PROPERTY_VIEW = "property_view"
    PROPERTY_CLICK = "property_click"
    TOOL_USE = "tool_use"
    EXPORT = "export"
    FAVORITE_ADD = "favorite_add"
    FAVORITE_REMOVE = "favorite_remove"
    MODEL_CHANGE = "model_change"
    ERROR = "error"


class UserActivitySummary(BaseModel):
    """Aggregated user activity summary."""

    period_start: datetime
    period_end: datetime
    total_searches: int = 0
    total_property_views: int = 0
    total_property_clicks: int = 0
    total_tool_uses: int = 0
    total_exports: int = 0
    total_favorites: int = 0
    unique_sessions: int = 0
    avg_processing_time_ms: Optional[float] = None
    top_tools: list[dict[str, Any]] = Field(default_factory=list)
    top_search_cities: list[dict[str, Any]] = Field(default_factory=list)
    event_counts_by_day: list[dict[str, Any]] = Field(default_factory=list)


class UserActivityTrendPoint(BaseModel):
    """Single point in activity trends."""

    date: str
    searches: int = 0
    property_views: int = 0
    tool_uses: int = 0
    exports: int = 0


class UserActivityTrendsResponse(BaseModel):
    """Activity trends over time."""

    trends: list[UserActivityTrendPoint] = Field(default_factory=list)
    interval: str = "day"  # day, week, month


# =============================================================================
# Model Preferences Per Task (Task #87)
# =============================================================================

# Task type for model preferences
TaskTypeType = Literal["chat", "search", "tools", "analysis", "embedding"]


class FallbackModelConfig(BaseModel):
    """Configuration for a fallback model in the chain."""

    provider: str = Field(
        ..., min_length=1, max_length=50, description="Provider name (e.g., 'openai', 'anthropic')"
    )
    model_name: str = Field(..., min_length=1, max_length=100, description="Model identifier")


class TaskModelPreferenceCreate(BaseModel):
    """Schema for creating a task model preference."""

    task_type: TaskTypeType = Field(
        ..., description="Task type (chat, search, tools, analysis, embedding)"
    )
    provider: str = Field(..., min_length=1, max_length=50, description="Primary provider name")
    model_name: str = Field(
        ..., min_length=1, max_length=100, description="Primary model identifier"
    )
    fallback_chain: Optional[list[FallbackModelConfig]] = Field(
        None,
        max_length=5,
        description="Ordered list of fallback models (max 5)",
    )
    is_active: bool = Field(default=True, description="Whether this preference is active")

    @field_validator("fallback_chain")
    @classmethod
    def validate_fallback_chain(
        cls, v: Optional[list[FallbackModelConfig]]
    ) -> Optional[list[FallbackModelConfig]]:
        """Validate fallback chain doesn't contain duplicates."""
        if v is None:
            return v

        # Check for duplicates in fallback chain
        seen = set()
        for item in v:
            key = (item.provider, item.model_name)
            if key in seen:
                raise ValueError(f"Duplicate fallback model: {item.provider}/{item.model_name}")
            seen.add(key)

        return v


class TaskModelPreferenceUpdate(BaseModel):
    """Schema for updating a task model preference."""

    provider: Optional[str] = Field(None, min_length=1, max_length=50)
    model_name: Optional[str] = Field(None, min_length=1, max_length=100)
    fallback_chain: Optional[list[FallbackModelConfig]] = Field(None, max_length=5)
    is_active: Optional[bool] = None

    @field_validator("fallback_chain")
    @classmethod
    def validate_fallback_chain(
        cls, v: Optional[list[FallbackModelConfig]]
    ) -> Optional[list[FallbackModelConfig]]:
        """Validate fallback chain doesn't contain duplicates."""
        if v is None:
            return v

        seen = set()
        for item in v:
            key = (item.provider, item.model_name)
            if key in seen:
                raise ValueError(f"Duplicate fallback model: {item.provider}/{item.model_name}")
            seen.add(key)

        return v


class TaskModelPreferenceResponse(BaseModel):
    """Schema for task model preference response."""

    id: str
    user_id: str
    task_type: str
    provider: str
    model_name: str
    fallback_chain: Optional[list[dict[str, str]]] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskModelPreferenceListResponse(BaseModel):
    """Schema for list of task model preferences."""

    items: list[TaskModelPreferenceResponse]
    total: int


class SystemDefaultModelPreference(BaseModel):
    """Schema for system default model preference."""

    task_type: str
    provider: str
    model_name: str
    description: Optional[str] = None
    cost_per_1m_input_tokens: Optional[float] = None
    cost_per_1m_output_tokens: Optional[float] = None


class SystemDefaultsResponse(BaseModel):
    """Schema for system default model preferences."""

    defaults: list[SystemDefaultModelPreference]
    available_providers: list[str]
    available_models: dict[str, list[str]]  # provider -> list of model names


class ModelCostEstimate(BaseModel):
    """Schema for estimated cost of using a model."""

    provider: str
    model_name: str
    input_cost_per_1m: Optional[float] = None
    output_cost_per_1m: Optional[float] = None
    estimated_tokens_per_request: int = 1000
    estimated_cost_per_request: Optional[float] = None


# =============================================================================
# CMA (Comparative Market Analysis) Schemas (Task #85)
# =============================================================================

# Type literals
CMAStatusType = Literal["draft", "completed", "expired"]
CMAAdjustmentCategoryType = Literal[
    "location", "size", "age", "condition", "amenities", "floor", "market"
]


class CMAAdjustmentModel(BaseModel):
    """Schema for a single CMA adjustment."""

    category: str = Field(..., description="Adjustment category")
    description: str = Field(..., description="Human-readable description")
    subject_value: Optional[str] = Field(None, description="Subject property value")
    comp_value: Optional[str] = Field(None, description="Comparable property value")
    adjustment_percent: float = Field(..., description="Adjustment percentage")
    adjustment_amount: float = Field(..., description="Adjustment in currency")
    confidence: float = Field(1.0, ge=0, le=1, description="Confidence level 0-1")

    model_config = {"from_attributes": True}


class CMAComparableResponse(BaseModel):
    """Schema for a comparable property in CMA."""

    property_id: str
    address: Optional[str] = None
    city: str
    district: Optional[str] = None
    price: float
    price_per_sqm: float
    currency: Optional[str] = Field(None, description="Currency of the price, e.g. PLN")
    area_sqm: Optional[float] = None
    rooms: Optional[float] = None
    year_built: Optional[int] = None
    property_type: str
    listing_date: Optional[datetime] = None
    listing_url: Optional[str] = None
    image_url: Optional[str] = None

    # Scoring
    similarity_score: float = Field(..., ge=0, le=100, description="Overall similarity score 0-100")
    score_breakdown: dict[str, float] = Field(
        default_factory=dict, description="Score breakdown by category"
    )
    distance_km: float = Field(0.0, description="Distance from subject in km")

    # Adjustments
    adjustments: list[CMAAdjustmentModel] = Field(default_factory=list)
    total_adjustment_percent: float = Field(0.0, description="Total adjustment percentage")
    total_adjustment_amount: float = Field(0.0, description="Total adjustment amount")
    adjusted_price: float = Field(..., description="Final adjusted price")

    model_config = {"from_attributes": True}


class CMAValuationResponse(BaseModel):
    """Schema for CMA valuation summary."""

    estimated_value: float = Field(..., description="Final estimated market value")
    value_range_low: float = Field(..., description="Conservative estimate (low)")
    value_range_high: float = Field(..., description="Optimistic estimate (high)")
    confidence_score: float = Field(..., ge=0, le=100, description="Confidence 0-100")
    price_per_sqm: float = Field(..., description="Estimated price per sqm")

    # Methodology
    method: str = Field(
        default="adjusted_comparable_sales",
        description="Valuation method used",
    )
    comparables_count: int = Field(..., ge=0, description="Number of comparables used")
    avg_adjusted_price: float = Field(0.0, description="Average of adjusted prices")
    median_adjusted_price: float = Field(0.0, description="Median of adjusted prices")
    std_deviation: float = Field(0.0, description="Standard deviation")

    model_config = {"from_attributes": True}


class CMAReportCreate(BaseModel):
    """Schema for creating a CMA report."""

    subject_property_id: str = Field(..., description="Subject property ID")
    comparable_ids: Optional[list[str]] = Field(
        None,
        max_length=10,
        description="Pre-selected comparable IDs. Auto-select if empty.",
    )
    max_distance_km: float = Field(
        default=5.0, ge=0.5, le=50, description="Max search radius in km"
    )
    min_comparables: int = Field(default=3, ge=3, le=10, description="Minimum comparables required")
    max_comparables: int = Field(
        default=6, ge=3, le=10, description="Maximum comparables to include"
    )
    include_pending: bool = Field(
        default=False,
        description="Include pending/under-offer listings",
    )
    custom_adjustments: Optional[dict[str, float]] = Field(
        None,
        description="Override default adjustment factors",
    )
    notes: Optional[str] = Field(None, max_length=2000, description="Additional notes")


class CMAReportResponse(BaseModel):
    """Schema for complete CMA report response."""

    id: str
    user_id: str
    status: CMAStatusType

    # Subject property
    subject_property_id: str
    subject_address: Optional[str] = None
    subject_city: str
    subject_district: Optional[str] = None
    subject_price: Optional[float] = None  # Current asking price
    subject_area_sqm: Optional[float] = None
    subject_rooms: Optional[float] = None
    subject_year_built: Optional[int] = None
    subject_property_type: str
    subject_energy_rating: Optional[str] = None
    subject_amenities: dict[str, bool] = Field(default_factory=dict)

    # Comparables
    comparables: list[CMAComparableResponse] = Field(default_factory=list)

    # Valuation
    valuation: CMAValuationResponse

    # Market context
    market_trend: Optional[str] = None  # rising, falling, stable
    market_avg_price_per_sqm: Optional[float] = None
    market_inventory_days: Optional[int] = None

    # Metadata
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class CMAReportListResponse(BaseModel):
    """Schema for paginated list of CMA reports."""

    items: list[CMAReportResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ComparableSearchRequest(BaseModel):
    """Schema for searching comparable properties."""

    property_id: str = Field(..., description="Subject property ID")
    max_distance_km: float = Field(default=5.0, ge=0.5, le=50)
    min_score: float = Field(default=50.0, ge=0, le=100)
    max_results: int = Field(default=10, ge=1, le=20)
    require_same_listing_type: bool = Field(default=True)


class ComparableSearchResponse(BaseModel):
    """Schema for comparable search results."""

    subject_property_id: str
    comparables: list[CMAComparableResponse]
    total_found: int
    search_params: dict[str, Any]


# =============================================================================
# Audit Log Schemas (Task #95)
# =============================================================================


class AuditLogEntryResponse(BaseModel):
    """Schema for a single audit log entry."""

    id: str
    actor_id: Optional[str] = None
    actor_email: Optional[str] = None
    actor_role: Optional[str] = None
    action: str
    resource: Optional[str] = None
    details: dict[str, Any] = {}
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_id: Optional[str] = None
    prev_hash: str
    entry_hash: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogListResponse(BaseModel):
    """Schema for paginated audit log list."""

    items: list[AuditLogEntryResponse]
    total: int
    limit: int
    offset: int


class ChainVerificationResponse(BaseModel):
    """Schema for hash-chain verification result."""

    valid: bool
    checked_count: int
    broken_count: int
    broken_entries: list[dict[str, Any]]


# ============================================================================
# Task #118: Search Feedback & Relevance Rating
# ============================================================================


class FeedbackCreate(BaseModel):
    """Schema for submitting a search result rating."""

    query: str = Field(
        ..., min_length=1, max_length=1000, description="Search query that produced the result"
    )
    property_id: str = Field(..., min_length=1, max_length=100, description="Rated property ID")
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 (poor) to 5 (excellent)")

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v: int) -> int:
        if v < 1 or v > 5:
            raise ValueError("Rating must be between 1 and 5")
        return v


class FeedbackResponse(BaseModel):
    """Schema for a submitted rating response."""

    id: str
    query: str
    property_id: str
    rating: int
    created_at: datetime

    model_config = {"from_attributes": True}


class RelevanceMetrics(BaseModel):
    """Aggregated relevance metrics for admin dashboard."""

    avg_rating: float = Field(..., description="Average rating across all feedback")
    total_ratings: int = Field(..., description="Total number of ratings")
    positive_pct: float = Field(..., description="Percentage of ratings 4-5 (positive)")
    ratings_by_score: dict[str, int] = Field(
        default_factory=dict, description="Count of ratings grouped by score (1-5)"
    )


# =============================================================================
# Task #113: Prioritized Lead Scoring Schemas
# =============================================================================


class LeadScoreInputSchema(BaseModel):
    """Schema for scoring a lead with budget fit and urgency."""

    budget_min: Optional[float] = Field(None, ge=0, description="Lead minimum budget")
    budget_max: Optional[float] = Field(None, ge=0, description="Lead maximum budget")
    target_price_min: Optional[float] = Field(None, ge=0, description="Target property min price")
    target_price_max: Optional[float] = Field(None, ge=0, description="Target property max price")
    searches: int = Field(0, ge=0, description="Number of searches performed")
    property_views: int = Field(0, ge=0, description="Number of properties viewed")
    favorites: int = Field(0, ge=0, description="Number of favorited properties")
    inquiries: int = Field(0, ge=0, description="Number of inquiries submitted")
    contact_requests: int = Field(0, ge=0, description="Number of contact requests")
    desired_move_date: Optional[str] = Field(
        None,
        max_length=100,
        description="Desired move timeline (e.g., 'asap', '1-3 months', ISO date)",
    )
    days_since_first_seen: int = Field(0, ge=0, description="Days since first seen")
    days_since_last_activity: int = Field(999, ge=0, description="Days since last activity")
    has_email: bool = Field(False, description="Lead has provided email")
    has_phone: bool = Field(False, description="Lead has provided phone")
    has_name: bool = Field(False, description="Lead has provided name")
    source: Optional[str] = Field(None, max_length=100, description="Lead source")
    agent_id: Optional[str] = Field(None, max_length=36, description="Assigned agent ID")
    property_id: Optional[str] = Field(None, max_length=255, description="Linked property ID")

    @field_validator("budget_max")
    @classmethod
    def validate_budget_range(cls, v: Optional[float], info) -> Optional[float]:
        """Ensure budget_max >= budget_min when both provided."""
        return v


class PrioritizedScoreResponse(BaseModel):
    """Schema for the prioritized lead scoring response."""

    score: float = Field(..., ge=0, le=100, description="Composite score (0-100)")
    budget_fit: float = Field(..., ge=0, le=100, description="Budget fit score (0-100)")
    urgency: float = Field(..., ge=0, le=100, description="Urgency score (0-100)")
    engagement: float = Field(..., ge=0, le=100, description="Engagement score (0-100)")
    priority_tier: str = Field(..., description="Priority tier: hot, warm, cool, cold")
    factors: dict[str, Any] = Field(default_factory=dict, description="Scoring factors used")
    recommendations: list[str] = Field(
        default_factory=list, description="Actionable recommendations"
    )


# LeadWithScoreResponse references PrioritizedScoreResponse as a forward
# reference, and the earlier model_rebuild() call (line ~1311) runs before this
# class exists — so it could not resolve the annotation then. Rebuild here, now
# that the referenced model is defined, or every instantiation of
# LeadWithScoreResponse raises PydanticUndefinedAnnotation.
# LeadDetailResponse inherits from LeadWithScoreResponse, so it needs the same
# treatment and the same moment.
LeadWithScoreResponse.model_rebuild()
LeadDetailResponse.model_rebuild()


class CreateAndScoreLeadRequest(BaseModel):
    """Schema for creating a lead and immediately scoring it."""

    visitor_id: str = Field(
        ..., min_length=1, max_length=36, description="Visitor UUID from cookie"
    )
    user_id: Optional[str] = Field(None, description="Linked user ID if registered")
    email: Optional[EmailStr] = Field(None, description="Lead email address")
    phone: Optional[str] = Field(None, max_length=50, description="Lead phone number")
    name: Optional[str] = Field(None, max_length=255, description="Lead name")
    source: Optional[str] = Field(None, max_length=100, description="Lead source")
    consent_given: bool = Field(default=False, description="GDPR consent status")
    # Scoring inputs
    budget_min: Optional[float] = Field(None, ge=0)
    budget_max: Optional[float] = Field(None, ge=0)
    target_price_min: Optional[float] = Field(None, ge=0)
    target_price_max: Optional[float] = Field(None, ge=0)
    desired_move_date: Optional[str] = Field(None, max_length=100)
    agent_id: Optional[str] = Field(None, max_length=36)
    property_id: Optional[str] = Field(None, max_length=255)


class LeadWithPriorityScoreResponse(LeadResponse):
    """Lead response with prioritized score breakdown."""

    priority_score: Optional[PrioritizedScoreResponse] = None


class AgentFunnelResponse(BaseModel):
    """Schema for agent lead funnel visualization."""

    agent_id: str
    total_leads: int
    by_priority: dict[str, int] = Field(
        default_factory=lambda: {"hot": 0, "warm": 0, "cool": 0, "cold": 0},
        description="Lead counts by priority tier",
    )
    by_status: dict[str, int] = Field(
        default_factory=lambda: {
            "new": 0,
            "contacted": 0,
            "qualified": 0,
            "converted": 0,
            "lost": 0,
        },
        description="Lead counts by status",
    )
    average_score: float = Field(0.0, description="Average lead score")
