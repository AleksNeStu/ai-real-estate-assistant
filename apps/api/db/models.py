"""SQLAlchemy models for user authentication."""

from datetime import UTC, datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, backref, mapped_column, relationship

from db.database import Base


class User(Base):
    """User model for authentication."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="user", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Account lockout fields (Task #47: Auth Security Hardening)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Profile fields (Task #88: User Profile Management)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Privacy settings (JSON for flexibility)
    privacy_settings: Mapped[dict] = mapped_column(
        JSON,
        default=lambda: {"profile_visible": True, "activity_visible": False},
        nullable=False,
    )

    # GDPR fields
    gdpr_consent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    data_export_requested_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )
    oauth_accounts: Mapped[list["OAuthAccount"]] = relationship(
        "OAuthAccount", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email})>"

    @property
    def is_locked(self) -> bool:
        """Check if account is currently locked due to failed login attempts."""
        if self.locked_until is None:
            return False
        return datetime.now(UTC) < self.locked_until


class RefreshToken(Base):
    """Refresh token model for JWT token rotation."""

    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")

    @property
    def is_revoked(self) -> bool:
        """Check if token is revoked."""
        return self.revoked_at is not None

    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        return datetime.now(UTC) >= self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if token is valid (not revoked and not expired)."""
        return not self.is_revoked and not self.is_expired

    def __repr__(self) -> str:
        return f"<RefreshToken(id={self.id}, user_id={self.user_id})>"


class OAuthAccount(Base):
    """OAuth account model for social login."""

    __tablename__ = "oauth_accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)  # google, apple
    provider_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="oauth_accounts")

    # Composite unique index for provider + provider_user_id
    __table_args__ = (
        Index("ix_oauth_accounts_provider_user", "provider", "provider_user_id", unique=True),
    )

    def __repr__(self) -> str:
        return f"<OAuthAccount(id={self.id}, provider={self.provider})>"


class PasswordResetToken(Base):
    """Password reset token model."""

    __tablename__ = "password_reset_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    @property
    def is_used(self) -> bool:
        """Check if token has been used."""
        return self.used_at is not None

    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        from datetime import UTC, datetime

        return datetime.now(UTC) >= self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if token is valid."""
        return not self.is_used and not self.is_expired

    def __repr__(self) -> str:
        return f"<PasswordResetToken(id={self.id}, user_id={self.user_id})>"


class EmailVerificationToken(Base):
    """Email verification token model."""

    __tablename__ = "email_verification_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    @property
    def is_used(self) -> bool:
        """Check if token has been used."""
        return self.used_at is not None

    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        from datetime import UTC, datetime

        return datetime.now(UTC) >= self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if token is valid."""
        return not self.is_used and not self.is_expired

    def __repr__(self) -> str:
        return f"<EmailVerificationToken(id={self.id}, user_id={self.user_id})>"


class SavedSearchDB(Base):
    """Database model for user saved searches."""

    __tablename__ = "saved_searches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Search criteria (stored as JSON)
    filters: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Alert settings
    alert_frequency: Mapped[str] = mapped_column(
        String(20), default="daily", nullable=False
    )  # instant, daily, weekly, none
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notify_on_new: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notify_on_price_drop: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    use_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", backref="saved_searches")

    def __repr__(self) -> str:
        return f"<SavedSearchDB(id={self.id}, user_id={self.user_id}, name={self.name})>"


class CollectionDB(Base):
    """Database model for user property collections (folders for favorites)."""

    __tablename__ = "collections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", backref="collections")
    favorites: Mapped[list["FavoriteDB"]] = relationship(
        "FavoriteDB", back_populates="collection", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_collections_user_default", "user_id", "is_default"),)

    def __repr__(self) -> str:
        return f"<CollectionDB(id={self.id}, user_id={self.user_id}, name={self.name})>"


class FavoriteDB(Base):
    """Database model for user property favorites."""

    __tablename__ = "favorites"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    property_id: Mapped[str] = mapped_column(
        String(255),  # String to match ChromaDB document IDs
        nullable=False,
        index=True,
    )
    collection_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("collections.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", backref="favorites")
    collection: Mapped[Optional["CollectionDB"]] = relationship(
        "CollectionDB", back_populates="favorites"
    )

    # Unique constraint: one user can favorite a property once
    __table_args__ = (Index("uq_favorites_user_property", "user_id", "property_id", unique=True),)

    def __repr__(self) -> str:
        return f"<FavoriteDB(id={self.id}, user_id={self.user_id}, property_id={self.property_id})>"


class PriceSnapshot(Base):
    """Database model for property price snapshots (price history tracking)."""

    __tablename__ = "price_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    property_id: Mapped[str] = mapped_column(
        String(255),  # String to match ChromaDB document IDs
        nullable=False,
        index=True,
    )
    price: Mapped[float] = mapped_column(Float, nullable=False)
    price_per_sqm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # ingestion source
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    # Composite index for efficient queries
    __table_args__ = (Index("ix_price_snapshots_property_recorded", "property_id", "recorded_at"),)

    def __repr__(self) -> str:
        return f"<PriceSnapshot(property_id={self.property_id}, price={self.price}, recorded_at={self.recorded_at})>"


class MarketAnomaly(Base):
    """Database model for detected market anomalies."""

    __tablename__ = "market_anomalies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # Anomaly classification
    anomaly_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # price_spike, price_drop, volume_spike, volume_drop
    severity: Mapped[str] = mapped_column(String(20), nullable=False)  # low, medium, high, critical

    # Scope (what entity has the anomaly)
    scope_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # property, city, district, market
    scope_id: Mapped[str] = mapped_column(
        String(255), nullable=False
    )  # property_id, city name, district name

    # Detection details
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    algorithm: Mapped[str] = mapped_column(String(50), nullable=False)  # z_score, iqr, seasonal
    threshold_used: Mapped[float] = mapped_column(Float, nullable=False)

    # Anomaly data
    metric_name: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # price, price_per_sqm, volume
    expected_value: Mapped[float] = mapped_column(Float, nullable=False)
    actual_value: Mapped[float] = mapped_column(Float, nullable=False)
    deviation_percent: Mapped[float] = mapped_column(Float, nullable=False)
    z_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Time periods for comparison
    baseline_period_start: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    baseline_period_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    comparison_period_start: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    comparison_period_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Alert tracking
    alert_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    alert_sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    dismissed_by: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True
    )  # user_id who dismissed
    dismissed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Additional context (property details, related anomalies, etc.)
    context: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Indexes for efficient queries
    __table_args__ = (
        Index("ix_anomalies_scope_detected", "scope_type", "scope_id", "detected_at"),
        Index("ix_anomalies_severity", "severity"),
        Index("ix_anomalies_type", "anomaly_type"),
    )

    def __repr__(self) -> str:
        return f"<MarketAnomaly(id={self.id}, type={self.anomaly_type}, severity={self.severity}, scope={self.scope_type}:{self.scope_id})>"


# =============================================================================
# Lead Scoring System Models (Task #55)
# =============================================================================


class Lead(Base):
    """Lead model for tracking all visitors (anonymous + registered).

    A lead represents a potential buyer/renter who has interacted with the platform.
    Can be anonymous (tracked via cookie) or registered user.
    """

    __tablename__ = "leads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # Visitor identification (cookie-based for anonymous users)
    visitor_id: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, index=True
    )  # Cookie UUID
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Contact information (optional, captured via forms)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Budget preferences
    budget_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    budget_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    preferred_locations: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # Lead status
    status: Mapped[str] = mapped_column(
        String(50), default="new", nullable=False
    )  # new, contacted, qualified, converted, lost
    source: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )  # organic, referral, ads, direct

    # Current score (denormalized for quick access)
    current_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Timestamps
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # GDPR compliance
    consent_given: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    consent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", backref="leads")
    interactions: Mapped[list["LeadInteraction"]] = relationship(
        "LeadInteraction", back_populates="lead", cascade="all, delete-orphan"
    )
    scores: Mapped[list["LeadScore"]] = relationship(
        "LeadScore", back_populates="lead", cascade="all, delete-orphan"
    )
    assignments: Mapped[list["AgentAssignment"]] = relationship(
        "AgentAssignment", back_populates="lead", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("ix_leads_status", "status"),
        Index("ix_leads_score", "current_score"),
        Index("ix_leads_last_activity", "last_activity_at"),
    )

    def __repr__(self) -> str:
        return f"<Lead(id={self.id}, visitor_id={self.visitor_id[:8]}..., score={self.current_score}, status={self.status})>"


class LeadInteraction(Base):
    """Lead interaction model for tracking all visitor behaviors.

    Records every interaction a lead has with the platform:
    - Searches performed
    - Properties viewed
    - Favorites added
    - Inquiries submitted
    - Contact requests
    """

    __tablename__ = "lead_interactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    lead_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Interaction type and details
    interaction_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # search, view, favorite, inquiry, contact, schedule_viewing
    property_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    search_query: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Additional context (filters used, form data, etc.)
    interaction_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Session information
    session_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    page_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    referrer: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)

    # Time spent (for view interactions, in seconds)
    time_spent_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False, index=True
    )

    # Relationships
    lead: Mapped["Lead"] = relationship("Lead", back_populates="interactions")

    # Indexes for common queries
    __table_args__ = (
        Index("ix_interactions_lead_type", "lead_id", "interaction_type"),
        Index("ix_interactions_lead_created", "lead_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<LeadInteraction(id={self.id}, lead_id={self.lead_id[:8]}..., type={self.interaction_type})>"


class LeadScore(Base):
    """Lead score model for tracking score history and breakdowns.

    Stores calculated scores with full explainability:
    - Total score (0-100)
    - Component scores (search activity, engagement, intent)
    - Factors that contributed to the score
    - AI-generated recommendations
    """

    __tablename__ = "lead_scores"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    lead_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Total composite score (0-100)
    total_score: Mapped[int] = mapped_column(Integer, nullable=False)

    # Component scores (0-100 each)
    search_activity_score: Mapped[int] = mapped_column(Integer, nullable=False)
    engagement_score: Mapped[int] = mapped_column(Integer, nullable=False)
    intent_score: Mapped[int] = mapped_column(Integer, nullable=False)

    # Detailed breakdown for explainability
    score_factors: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict
    )  # {"search_count": 15, "favorites": 3, "views": 42, ...}

    # AI-generated insights and recommendations
    recommendations: Mapped[Optional[list]] = mapped_column(
        JSON, nullable=True
    )  # ["High interest in Berlin apartments", ...]

    # Model version for tracking scoring algorithm changes
    model_version: Mapped[str] = mapped_column(String(20), default="1.0.0", nullable=False)

    # Timestamp
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False, index=True
    )

    # Relationships
    lead: Mapped["Lead"] = relationship("Lead", back_populates="scores")

    # Indexes
    __table_args__ = (Index("ix_scores_lead_calculated", "lead_id", "calculated_at"),)

    def __repr__(self) -> str:
        return f"<LeadScore(id={self.id}, lead_id={self.lead_id[:8]}..., total={self.total_score})>"


class AgentAssignment(Base):
    """Agent assignment model for assigning leads to agents.

    Supports:
    - Multiple agents per lead (team approach)
    - Primary agent designation
    - Assignment history tracking
    """

    __tablename__ = "agent_assignments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    lead_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    agent_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Assignment details
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    assigned_by: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Status tracking
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    unassigned_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    unassigned_by: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    lead: Mapped["Lead"] = relationship("Lead", back_populates="assignments")
    agent: Mapped["User"] = relationship("User", foreign_keys=[agent_id], backref="assigned_leads")
    assigner: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[assigned_by], backref="assigned_by_me"
    )

    # Ensure one primary agent per lead
    __table_args__ = (
        Index("uq_assignments_lead_primary", "lead_id", "is_active", "is_primary", unique=False),
        Index("ix_assignments_agent_active", "agent_id", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<AgentAssignment(lead_id={self.lead_id[:8]}..., agent_id={self.agent_id[:8]}..., primary={self.is_primary})>"


# =============================================================================
# Agent Performance Analytics Models (Task #56)
# =============================================================================


class Deal(Base):
    """Deal model for tracking closed transactions.

    Created when a lead's status changes to 'converted'.
    Tracks the full deal lifecycle from offer to closing.
    """

    __tablename__ = "deals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # Lead reference
    lead_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Property reference (nullable - may be off-platform deal)
    property_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Agent reference
    #
    # The rule says "the deal stays, the agent link goes" - which only works
    # if the column can hold a null. It could not, so the rule could never be
    # carried out: with foreign keys enforced the parent's delete was refused
    # with "NOT NULL constraint failed". A deal outlives its agent.
    agent_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Deal details
    deal_type: Mapped[str] = mapped_column(String(20), nullable=False)  # sale, rent
    property_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    property_city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    property_district: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Financial
    deal_value: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="EUR")

    # Deal stages
    status: Mapped[str] = mapped_column(
        String(20), default="offer_submitted", nullable=False
    )  # offer_submitted, offer_accepted, contract_signed, closed, fell_through

    # Timestamps for time tracking
    offer_submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    offer_accepted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    contract_signed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Metadata
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    lead: Mapped["Lead"] = relationship("Lead", backref="deals")
    agent: Mapped[Optional["User"]] = relationship("User", backref="deals")
    commissions: Mapped[list["Commission"]] = relationship(
        "Commission", back_populates="deal", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_deals_agent_status", "agent_id", "status"),
        Index("ix_deals_closed_at", "closed_at"),
    )

    def __repr__(self) -> str:
        return f"<Deal(id={self.id}, agent_id={self.agent_id[:8] if self.agent_id else 'None'}..., value={self.deal_value}, status={self.status})>"


class Commission(Base):
    """Commission model for tracking agent earnings.

    Supports split commissions and tiered rates.
    """

    __tablename__ = "commissions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # References
    deal_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("deals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    agent_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Commission details
    commission_type: Mapped[str] = mapped_column(
        String(20), default="primary"
    )  # primary, split, referral
    commission_rate: Mapped[float] = mapped_column(Float, nullable=False)  # e.g., 0.03 for 3%
    commission_amount: Mapped[float] = mapped_column(Float, nullable=False)

    # Status
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False
    )  # pending, approved, paid, clawed_back

    # Payment tracking
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    payment_reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Metadata
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    deal: Mapped["Deal"] = relationship("Deal", back_populates="commissions")
    agent: Mapped[Optional["User"]] = relationship("User", backref="commissions")

    def __repr__(self) -> str:
        return f"<Commission(id={self.id}, deal_id={self.deal_id[:8]}..., amount={self.commission_amount}, status={self.status})>"


class AgentGoal(Base):
    """Agent goal model for tracking performance targets.

    Supports multiple goal types (leads, deals, revenue).
    """

    __tablename__ = "agent_goals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    agent_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Goal details
    goal_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # leads, deals, revenue, gci (gross commission income)
    target_value: Mapped[float] = mapped_column(Float, nullable=False)
    current_value: Mapped[float] = mapped_column(Float, default=0)

    # Period
    period_type: Mapped[str] = mapped_column(
        String(10), nullable=False
    )  # daily, weekly, monthly, quarterly, yearly
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    achieved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    agent: Mapped[Optional["User"]] = relationship("User", backref="goals")

    __table_args__ = (
        Index("ix_agent_goals_agent_active", "agent_id", "is_active"),
        Index("ix_agent_goals_period", "period_start", "period_end"),
    )

    def __repr__(self) -> str:
        return f"<AgentGoal(id={self.id}, agent_id={self.agent_id[:8]}..., type={self.goal_type}, target={self.target_value})>"


# =============================================================================
# Push Notification System Models (Task #63)
# =============================================================================


class PushSubscription(Base):
    """Web Push subscription for browser notifications.

    Stores browser push subscription data for sending web push notifications
    to users about price drops, new properties, and market anomalies.
    """

    __tablename__ = "push_subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Push subscription data (from browser PushSubscription JSON)
    endpoint: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    p256dh: Mapped[str] = mapped_column(String(255), nullable=False)  # VAPID p256dh key
    auth: Mapped[str] = mapped_column(String(255), nullable=False)  # VAPID auth secret

    # Device metadata
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    device_name: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )  # "Chrome on Windows", etc.

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", backref="push_subscriptions")

    # Indexes
    __table_args__ = (Index("ix_push_user_active", "user_id", "is_active"),)

    def __repr__(self) -> str:
        return f"<PushSubscription(id={self.id[:8]}..., user_id={self.user_id[:8]}..., active={self.is_active})>"


# =============================================================================
# Notification Preferences System Models (Task #86)
# =============================================================================


class NotificationPreferenceDB(Base):
    """Database model for user notification preferences.

    Stores granular notification settings including type toggles,
    frequency settings, channel selection, and unsubscribe management.
    """

    __tablename__ = "notification_preferences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Notification type toggles
    price_alerts_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    new_listings_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    saved_search_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    market_updates_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Frequency settings
    alert_frequency: Mapped[str] = mapped_column(
        String(20), default="daily", nullable=False
    )  # instant, daily, weekly

    # Channel selection
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    push_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    in_app_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Advanced settings
    quiet_hours_start: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)  # HH:MM
    quiet_hours_end: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)  # HH:MM
    price_drop_threshold: Mapped[float] = mapped_column(
        Float, default=5.0, nullable=False
    )  # Percent

    # Digest settings
    daily_digest_time: Mapped[str] = mapped_column(
        String(5), default="09:00", nullable=False
    )  # HH:MM
    weekly_digest_day: Mapped[str] = mapped_column(String(10), default="monday", nullable=False)

    # Expert/Marketing preferences
    expert_mode: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    marketing_emails: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Unsubscribe management
    unsubscribe_token: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
        default=lambda: str(uuid4()).replace("-", "") + str(uuid4()).replace("-", ""),
    )
    unsubscribed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    unsubscribed_types: Mapped[Optional[list]] = mapped_column(
        JSON, nullable=True, default=list
    )  # ["marketing", "price_alerts", ...]

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", backref="notification_preferences")

    __table_args__ = (Index("ix_notification_prefs_unsubscribe_token", "unsubscribe_token"),)

    def __repr__(self) -> str:
        return f"<NotificationPreferenceDB(id={self.id[:8]}..., user_id={self.user_id[:8]}..., frequency={self.alert_frequency})>"

    @property
    def is_fully_unsubscribed(self) -> bool:
        """Check if user has fully unsubscribed from all notifications."""
        return self.unsubscribed_at is not None


# =============================================================================
# Agent/Broker System Models (Task #45)
# =============================================================================


class AgentProfile(Base):
    """Agent/broker professional profile linked to User.

    Stores professional information for real estate agents including
    agency details, specializations, ratings, and contact information.
    """

    __tablename__ = "agent_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Professional Information
    agency_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    agency_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True, index=True
    )  # For multi-tenancy
    license_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    license_state: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # For regional licensing

    # Contact (professional, can differ from User.email)
    professional_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    professional_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    office_address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Specialization
    specialties: Mapped[Optional[list]] = mapped_column(
        JSON, nullable=True
    )  # ["residential", "commercial", "luxury"]
    service_areas: Mapped[Optional[list]] = mapped_column(
        JSON, nullable=True
    )  # ["Berlin", "Munich"]
    property_types: Mapped[Optional[list]] = mapped_column(
        JSON, nullable=True
    )  # ["apartment", "house", "investment"]
    languages: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)  # ["en", "de", "pl"]

    # Rating & Reviews
    average_rating: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_reviews: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_sales: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # Track record
    total_rentals: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Status
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    verification_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Media
    profile_image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", backref="agent_profile")
    listings: Mapped[list["AgentListing"]] = relationship(
        "AgentListing", back_populates="agent", cascade="all, delete-orphan"
    )
    inquiries: Mapped[list["AgentInquiry"]] = relationship(
        "AgentInquiry", back_populates="agent", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_agent_profiles_agency", "agency_id"),
        Index("ix_agent_profiles_rating", "average_rating"),
    )

    def __repr__(self) -> str:
        return f"<AgentProfile(id={self.id[:8]}..., user_id={self.user_id[:8]}..., agency={self.agency_name})>"


class AgentListing(Base):
    """Links agents to properties they represent.

    An agent can have multiple listings, and a property can have
    multiple agents (co-listing). Supports both sale and rental listings.
    """

    __tablename__ = "agent_listings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    agent_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("agent_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    property_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,  # ChromaDB property ID
    )
    listing_type: Mapped[str] = mapped_column(
        String(20), default="sale", nullable=False
    )  # sale, rent, both
    is_primary: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )  # Primary agent for property
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    commission_rate: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )  # Optional override
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    # Relationships
    agent: Mapped["AgentProfile"] = relationship("AgentProfile", back_populates="listings")

    __table_args__ = (Index("uq_agent_listing", "agent_id", "property_id", unique=True),)

    def __repr__(self) -> str:
        return f"<AgentListing(agent_id={self.agent_id[:8]}..., property_id={self.property_id[:8]}..., type={self.listing_type})>"


class AgentInquiry(Base):
    """Contact inquiries sent to agents.

    Stores all contact form submissions from users/visitors to agents.
    Can be linked to a specific property or be general inquiries.
    """

    __tablename__ = "agent_inquiries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    agent_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("agent_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Inquirer info (can be anonymous or registered)
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    visitor_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True, index=True
    )  # For anonymous
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Inquiry details
    property_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    inquiry_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # general, property, financing
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # Status
    status: Mapped[str] = mapped_column(
        String(20), default="new", nullable=False
    )  # new, read, responded, closed

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    responded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    agent: Mapped["AgentProfile"] = relationship("AgentProfile", back_populates="inquiries")
    user: Mapped[Optional["User"]] = relationship("User", backref="agent_inquiries")

    __table_args__ = (
        Index("ix_inquiries_status", "status"),
        Index("ix_inquiries_created", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<AgentInquiry(id={self.id[:8]}..., agent_id={self.agent_id[:8]}..., type={self.inquiry_type}, status={self.status})>"


class ViewingAppointment(Base):
    """Scheduled property viewings with agents.

    Manages viewing appointment requests, confirmations, and cancellations.
    Supports both registered users and anonymous visitors.
    """

    __tablename__ = "viewing_appointments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    agent_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("agent_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Client info
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    visitor_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    client_name: Mapped[str] = mapped_column(String(255), nullable=False)
    client_email: Mapped[str] = mapped_column(String(255), nullable=False)
    client_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Property
    property_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Scheduling
    proposed_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    confirmed_datetime: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60, nullable=False)

    # Status
    status: Mapped[str] = mapped_column(
        String(20), default="requested", nullable=False
    )  # requested, confirmed, cancelled, completed
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cancellation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    agent: Mapped["AgentProfile"] = relationship("AgentProfile", backref="viewing_appointments")
    user: Mapped[Optional["User"]] = relationship("User", backref="viewing_appointments")

    __table_args__ = (
        Index("ix_appointments_datetime", "proposed_datetime"),
        Index("ix_appointments_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<ViewingAppointment(id={self.id[:8]}..., agent_id={self.agent_id[:8]}..., status={self.status})>"


# =============================================================================
# Document Management System Models (Task #43)
# =============================================================================


class DocumentDB(Base):
    """Document model for user property-related documents.

    Stores metadata for uploaded documents including contracts,
    inspection reports, photos, and other property-related files.
    Supports OCR text extraction for searchability.
    """

    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # User reference (required)
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Property reference (optional - document may not be linked to a specific property)
    property_id: Mapped[Optional[str]] = mapped_column(
        String(255),  # String to match ChromaDB document IDs
        nullable=True,
        index=True,
    )

    # File information
    filename: Mapped[str] = mapped_column(String(255), nullable=False)  # Unique stored filename
    original_filename: Mapped[str] = mapped_column(
        String(255), nullable=False
    )  # Original upload name
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)  # MIME type
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)  # Size in bytes
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)  # Path to stored file

    # Document metadata
    category: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # contract, inspection, photo, financial, other
    tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array of tags
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # OCR fields
    extracted_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # OCR extracted text
    ocr_status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False
    )  # pending, processing, completed, failed

    # Expiry tracking
    expiry_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expiry_notified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", backref="documents")

    # Indexes
    __table_args__ = (
        Index("ix_documents_category", "category"),
        Index("ix_documents_ocr_status", "ocr_status"),
        Index("ix_documents_expiry", "expiry_date"),
    )

    def __repr__(self) -> str:
        return f"<DocumentDB(id={self.id[:8]}..., user_id={self.user_id[:8]}..., filename={self.original_filename[:20]}...)>"


class DocumentTemplateDB(Base):
    """Document templates with Jinja2 placeholders for e-signature.

    Stores reusable document templates (rental agreements, purchase offers, etc.)
    that can be rendered with variable substitution.
    """

    __tablename__ = "document_templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Template info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    template_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # rental_agreement, purchase_offer, lease_renewal, custom

    # Template content (Jinja2 HTML)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Variable definitions (JSON schema for validation)
    variables: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Default template flag
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", backref="document_templates")

    # Indexes
    __table_args__ = (
        Index("ix_document_templates_type", "template_type"),
        Index("ix_document_templates_user_type", "user_id", "template_type"),
    )

    def __repr__(self) -> str:
        return f"<DocumentTemplateDB(id={self.id[:8]}..., name={self.name[:30]}, type={self.template_type})>"


class SignatureRequestDB(Base):
    """E-signature request tracking.

    Tracks signature requests sent via external providers (HelloSign, DocuSign).
    Stores signer information, status, and provider integration details.
    """

    __tablename__ = "signature_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Source document/template
    document_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    template_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("document_templates.id", ondelete="SET NULL"), nullable=True
    )

    # Provider info
    provider: Mapped[str] = mapped_column(String(50), nullable=False)  # hellosign, docusign
    provider_envelope_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Document details
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    property_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)

    # Rendered document metadata
    document_content_hash: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True
    )  # SHA-256

    # Signers (JSON array: [{email, name, role, order, status, signed_at}])
    signers: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    # Template variables used
    variables: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(50), default="draft", nullable=False
    )  # draft, sent, viewed, partially_signed, completed, expired, cancelled, declined
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    viewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Reminder tracking
    reminder_sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reminder_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", backref="signature_requests")
    document: Mapped[Optional["DocumentDB"]] = relationship(
        "DocumentDB", backref="signature_requests"
    )
    template: Mapped[Optional["DocumentTemplateDB"]] = relationship(
        "DocumentTemplateDB", backref="signature_requests"
    )
    signed_document: Mapped[Optional["SignedDocumentDB"]] = relationship(
        "SignedDocumentDB", backref="signature_request", uselist=False
    )

    # Indexes
    __table_args__ = (
        Index("ix_signature_requests_status", "status"),
        Index("ix_signature_requests_provider", "provider", "provider_envelope_id"),
        Index("ix_signature_requests_expires", "expires_at"),
    )

    def __repr__(self) -> str:
        return f"<SignatureRequestDB(id={self.id[:8]}..., title={self.title[:30]}, status={self.status})>"


class SignedDocumentDB(Base):
    """Final signed documents storage.

    Stores the completed, signed document with verification metadata.
    """

    __tablename__ = "signed_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    signature_request_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("signature_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )

    # Storage
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)

    # Provider metadata
    provider_document_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    certificate_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Verification
    signature_hash: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True
    )  # Hash for integrity

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    # Relationships
    document: Mapped[Optional["DocumentDB"]] = relationship(
        "DocumentDB", backref="signed_documents"
    )

    def __repr__(self) -> str:
        return f"<SignedDocumentDB(id={self.id[:8]}..., request_id={self.signature_request_id[:8]}...)>"


class FilterPresetDB(Base):
    """Database model for user filter presets (Task #75: Advanced Filter Presets).

    Stores saveable filter combinations for quick access to common search patterns.
    Unlike SavedSearchDB, presets are lightweight and focused on quick UI access
    without alert/notification overhead.
    """

    __tablename__ = "filter_presets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Filter configuration (stored as JSON)
    # Keys: city, min_price, max_price, rooms, property_type, has_parking, etc.
    filters: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Default preset flag (only one per user)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Usage tracking for analytics/sorting
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    use_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", backref="filter_presets")

    def __repr__(self) -> str:
        return f"<FilterPresetDB(id={self.id}, user_id={self.user_id}, name={self.name})>"


# =============================================================================
# Search Result Ranking System Models (Task #76)
# =============================================================================


class RankingConfig(Base):
    """Runtime-configurable ranking weights for search results.

    Stores configurable parameters for the hybrid search and reranking pipeline.
    Supports A/B testing through named configurations and activation flags.
    """

    __tablename__ = "ranking_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Hybrid search weights (BM25 + semantic fusion)
    alpha: Mapped[float] = mapped_column(
        Float, default=0.7, nullable=False
    )  # vector vs keyword (0.7 = 70% vector)

    # Reranker boost factors
    boost_exact_match: Mapped[float] = mapped_column(Float, default=1.5, nullable=False)
    boost_metadata_match: Mapped[float] = mapped_column(Float, default=1.3, nullable=False)
    boost_quality_signals: Mapped[float] = mapped_column(Float, default=1.2, nullable=False)
    diversity_penalty: Mapped[float] = mapped_column(Float, default=0.9, nullable=False)

    # Additional ranking signals (new)
    weight_recency: Mapped[float] = mapped_column(Float, default=0.1, nullable=False)  # listing age
    weight_price_match: Mapped[float] = mapped_column(
        Float, default=0.15, nullable=False
    )  # budget proximity
    weight_location: Mapped[float] = mapped_column(
        Float, default=0.1, nullable=False
    )  # distance to preferred areas

    # Personalization settings
    personalization_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    personalization_weight: Mapped[float] = mapped_column(
        Float, default=0.2, nullable=False
    )  # 0-0.5 range

    # Activation and metadata
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    experiments_as_control: Mapped[list["ABExperiment"]] = relationship(
        "ABExperiment",
        foreign_keys="ABExperiment.control_config_id",
        back_populates="control_config",
    )
    experiments_as_treatment: Mapped[list["ABExperiment"]] = relationship(
        "ABExperiment",
        foreign_keys="ABExperiment.treatment_config_id",
        back_populates="treatment_config",
    )

    __table_args__ = (
        Index("ix_ranking_configs_active", "is_active"),
        Index("ix_ranking_configs_default", "is_default"),
    )

    def __repr__(self) -> str:
        return f"<RankingConfig(id={self.id[:8]}..., name={self.name}, alpha={self.alpha}, active={self.is_active})>"


class ABExperiment(Base):
    """A/B test experiment definition for ranking experiments.

    Supports controlled experiments to compare ranking algorithms
    with configurable traffic splits and targeting.
    """

    __tablename__ = "ab_experiments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Experiment configuration
    control_config_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("ranking_configs.id", ondelete="RESTRICT"), nullable=False
    )
    treatment_config_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("ranking_configs.id", ondelete="RESTRICT"), nullable=False
    )

    # Traffic allocation
    traffic_split: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)  # 0.5 = 50/50

    # Experiment lifecycle
    status: Mapped[str] = mapped_column(
        String(20), default="draft", nullable=False
    )  # draft, running, completed, archived
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Targeting rules (JSON with conditions)
    target_user_segments: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True
    )  # e.g., {"countries": ["PL"], "user_types": ["registered"]}

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    control_config: Mapped["RankingConfig"] = relationship(
        "RankingConfig", foreign_keys=[control_config_id], back_populates="experiments_as_control"
    )
    treatment_config: Mapped["RankingConfig"] = relationship(
        "RankingConfig",
        foreign_keys=[treatment_config_id],
        back_populates="experiments_as_treatment",
    )
    assignments: Mapped[list["ABExperimentAssignment"]] = relationship(
        "ABExperimentAssignment", back_populates="experiment", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_ab_experiments_status", "status"),
        Index("ix_ab_experiments_dates", "start_date", "end_date"),
    )

    def __repr__(self) -> str:
        return f"<ABExperiment(id={self.id[:8]}..., name={self.name}, status={self.status})>"


class ABExperimentAssignment(Base):
    """User assignment to experiment variant.

    Ensures consistent assignment per session/user using deterministic hashing.
    """

    __tablename__ = "ab_experiment_assignments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    experiment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("ab_experiments.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # User/session identification
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    session_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Assignment details
    variant: Mapped[str] = mapped_column(String(20), nullable=False)  # "control" or "treatment"
    config_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("ranking_configs.id", ondelete="RESTRICT"), nullable=False
    )

    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    # Relationships
    experiment: Mapped["ABExperiment"] = relationship("ABExperiment", back_populates="assignments")
    config: Mapped["RankingConfig"] = relationship("RankingConfig")

    # Ensure unique assignment per experiment/session
    __table_args__ = (
        Index("uq_ab_assignments_experiment_session", "experiment_id", "session_id", unique=True),
    )

    def __repr__(self) -> str:
        return f"<ABExperimentAssignment(experiment_id={self.experiment_id[:8]}..., session={self.session_id[:8]}..., variant={self.variant})>"


class SearchEvent(Base):
    """Search event tracking for quality metrics.

    Records each search with full context for calculating CTR, MRR, NDCG.
    """

    __tablename__ = "search_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # Context
    session_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    experiment_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("ab_experiments.id", ondelete="SET NULL"), nullable=True
    )
    ranking_config_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("ranking_configs.id", ondelete="RESTRICT"), nullable=False
    )

    # Query information
    query: Mapped[str] = mapped_column(Text, nullable=False)
    filters: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Results
    results_count: Mapped[int] = mapped_column(Integer, nullable=False)
    results_property_ids: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list
    )  # Ordered list

    # Performance
    processing_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)

    # Timestamp
    search_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False, index=True
    )

    # Relationships
    ranking_config: Mapped["RankingConfig"] = relationship("RankingConfig")
    interactions: Mapped[list["SearchResultInteraction"]] = relationship(
        "SearchResultInteraction", back_populates="search_event", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_search_events_session_timestamp", "session_id", "search_timestamp"),
        Index("ix_search_events_config_timestamp", "ranking_config_id", "search_timestamp"),
    )

    def __repr__(self) -> str:
        return f"<SearchEvent(id={self.id[:8]}..., query={self.query[:30]}..., results={self.results_count})>"


class SearchResultInteraction(Base):
    """User interactions with search results.

    Tracks views, clicks, favorites for calculating quality metrics.
    """

    __tablename__ = "search_result_interactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    search_event_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("search_events.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Property and position
    property_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)  # 0-indexed position in results

    # Interaction types
    viewed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    view_duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    clicked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    favorited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    contacted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # Via lead form

    interaction_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    # Relationships
    search_event: Mapped["SearchEvent"] = relationship("SearchEvent", back_populates="interactions")

    __table_args__ = (
        Index("ix_search_interactions_property", "property_id"),
        Index(
            "ix_search_interactions_search_property", "search_event_id", "property_id", unique=True
        ),
    )

    def __repr__(self) -> str:
        return f"<SearchResultInteraction(search_event={self.search_event_id[:8]}..., property={self.property_id[:8]}..., pos={self.position})>"


class UserPreferenceProfile(Base):
    """Aggregated user preferences for personalized ranking.

    Built from user behavior (views, favorites, searches) and updated periodically.
    """

    __tablename__ = "user_preference_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # Location preferences (weighted list)
    preferred_cities: Mapped[Optional[list]] = mapped_column(
        JSON, nullable=True
    )  # [{"city": "Warsaw", "weight": 0.8}, ...]

    # Budget preferences
    preferred_price_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    preferred_price_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Property characteristics
    preferred_rooms: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)  # [2, 3]
    preferred_property_types: Mapped[Optional[list]] = mapped_column(
        JSON, nullable=True
    )  # ["apartment", "house"]

    # Amenity preferences (weights for each amenity)
    amenity_weights: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True
    )  # {"has_parking": 0.8, "has_garden": 0.6}

    # Search patterns
    common_query_patterns: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # Embedding for similarity-based personalization (stored as bytes)
    preference_embedding: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    embedding_updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Statistics
    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    favorite_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    search_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", backref="preference_profile")

    def __repr__(self) -> str:
        return f"<UserPreferenceProfile(user_id={self.user_id[:8]}..., views={self.view_count}, favorites={self.favorite_count})>"


# =============================================================================
# Buyer Memory Models (Task #76)
# =============================================================================


class BuyerMemoryFact(Base):
    """One durable fact the assistant learned about a buyer (Task #76).

    The facts a buyer states and never repeats: the budget, the areas they ruled
    out, what they liked about a specific listing. Without them the assistant
    forgets every turn the moment the session ends.

    Kinds: budget | ruled_out_area | liked | disliked | requirement | note
    Sources: chat | manual | derived
    """

    __tablename__ = "buyer_memory_facts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # The fact itself
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)  # in the buyer's own words
    listing_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    source: Mapped[str] = mapped_column(String(32), default="chat", nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    # passive_deletes on the backref: the facts are removed by the database's
    # ON DELETE CASCADE, so the ORM must not try to null out a non-nullable FK.
    user: Mapped["User"] = relationship(
        "User", backref=backref("buyer_memories", passive_deletes=True)
    )

    def __repr__(self) -> str:
        return f"<BuyerMemoryFact(user_id={self.user_id[:8]}..., kind={self.kind})>"


# =============================================================================
# Data Source Management Models (Task #79)
# =============================================================================


class DataSourceDB(Base):
    """Database model for tracking configured data sources.

    Stores configuration and status for all property data ingestion sources:
    - File uploads (CSV, Excel, JSON)
    - URL-based imports
    - Portal API connections
    """

    __tablename__ = "data_sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # Source identification
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Source type: 'file_upload', 'url', 'portal_api', 'json'
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Source configuration (JSON)
    # For file_upload: {"filename": "...", "size_bytes": ..., "sheet_name": "..."}
    # For url: {"url": "...", "sheet_name": "...", "header_row": 0}
    # For portal_api: {"portal": "otodom", "city": "Warsaw", "filters": {...}}
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False, index=True
    )  # pending, active, syncing, error, disabled

    # Sync tracking
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_status: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )  # success, failed, partial
    last_sync_duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Statistics
    total_records: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_records_synced: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Health indicators
    health_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # 0-100
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Scheduling (for future cron integration)
    sync_schedule: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # cron expression
    auto_sync_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    sync_history: Mapped[list["DataSourceSyncHistory"]] = relationship(
        "DataSourceSyncHistory", back_populates="data_source", cascade="all, delete-orphan"
    )

    # Indexes (status and source_type have inline index=True)
    __table_args__ = (Index("ix_data_sources_created", "created_at"),)

    def __repr__(self) -> str:
        return f"<DataSourceDB(id={self.id[:8]}..., name={self.name[:30]}, type={self.source_type}, status={self.status})>"


class DataSourceSyncHistory(Base):
    """Track sync history for each data source.

    Records each sync operation with timing, results, and error details.
    Used for health score calculation and debugging.
    """

    __tablename__ = "data_source_sync_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    data_source_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("data_sources.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Sync details
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # running, success, failed, partial

    # Results
    records_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_added: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_updated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_skipped: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Error tracking
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    data_source: Mapped["DataSourceDB"] = relationship(
        "DataSourceDB", back_populates="sync_history"
    )

    # Indexes
    __table_args__ = (Index("ix_sync_history_source_started", "data_source_id", "started_at"),)

    def __repr__(self) -> str:
        return f"<DataSourceSyncHistory(id={self.id[:8]}..., source_id={self.data_source_id[:8]}..., status={self.status})>"


# =============================================================================
# Bulk Import/Export Job Models (Task #80)
# =============================================================================


class BulkJob(Base):
    """Database model for tracking async bulk import/export jobs.

    Stores job status, progress, and results for long-running operations
    that are executed in the background using FastAPI BackgroundTasks.
    """

    __tablename__ = "bulk_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # Job identification
    job_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # import, export
    source_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # url, file_upload, portal_api, search

    # User who initiated the job
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Job configuration
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False, index=True
    )  # pending, running, completed, failed, cancelled

    # Progress tracking
    records_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    progress_percent: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Results
    result_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # Download URL
    result_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Summary stats

    # Error tracking
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )  # For result cleanup

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", backref="bulk_jobs")

    # Indexes
    __table_args__ = (
        Index("ix_bulk_jobs_type_status", "job_type", "status"),
        Index("ix_bulk_jobs_created", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<BulkJob(id={self.id[:8]}..., type={self.job_type}, status={self.status}, progress={self.progress_percent}%)>"


# =============================================================================
# User Activity Analytics Models (Task #82)
# =============================================================================


class UserActivityEvent(Base):
    """User activity events for analytics (Task #82).

    Tracks feature usage, tool invocations, and custom events
    that are not covered by SearchEvent.
    """

    __tablename__ = "user_activity_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # User context (hashed for privacy)
    user_id_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    session_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Event details
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    event_category: Mapped[str] = mapped_column(String(50), nullable=False)
    event_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Performance tracking
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Timestamp
    event_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False, index=True
    )

    __table_args__ = (
        Index("ix_user_activity_session_timestamp", "session_id", "event_timestamp"),
        Index("ix_user_activity_type_timestamp", "event_type", "event_timestamp"),
    )

    def __repr__(self) -> str:
        return f"<UserActivityEvent(id={self.id[:8]}..., type={self.event_type}, session={self.session_id[:8]}...)>"


# =============================================================================
# Model Preferences Per Task (Task #87)
# =============================================================================

# Task type enumeration for model preferences
TASK_TYPES = ("chat", "search", "tools", "analysis", "embedding")


class TaskModelPreference(Base):
    """Model preference per task type (Task #87).

    Allows users to configure different LLM models for different
    task types (chat, search, tools, analysis).
    """

    __tablename__ = "task_model_preferences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # User association
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Task configuration
    task_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Fallback chain (ordered list of {provider, model_name} dicts)
    fallback_chain: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    __table_args__ = (
        # Unique constraint: one preference per task type per user
        Index("ix_task_model_pref_user_task", "user_id", "task_type", unique=True),
    )

    def __repr__(self) -> str:
        return f"<TaskModelPreference(user={self.user_id[:8]}..., task={self.task_type}, model={self.provider}/{self.model_name})>"


class CMAReportDB(Base):
    """
    Comparative Market Analysis (CMA) report storage.

    Stores generated CMA reports with subject property data,
    selected comparables, adjustments, and final valuation.
    """

    __tablename__ = "cma_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # User association
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Report status
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft", index=True)
    # Values: draft, completed, expired

    # Subject property reference
    subject_property_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    # Snapshot of subject property at report creation time
    subject_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Comparable properties with scores and adjustments
    # Structure: [{"property_id": str, "similarity_score": float, "adjustments": [...], "adjusted_price": float}]
    comparables: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    # Final valuation result
    # Structure: {"estimated_value": float, "value_range_low": float, "value_range_high": float, "confidence_score": float, "price_per_sqm": float}
    valuation: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Market context at report time (optional)
    # Structure: {"avg_price_per_sqm": float, "median_price": float, "trend": str, "inventory_count": int}
    market_context: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    # Relationships
    user: Mapped["User"] = relationship("User", backref="cma_reports")

    __table_args__ = (
        Index("ix_cma_reports_user_status", "user_id", "status"),
        Index("ix_cma_reports_user_created", "user_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<CMAReport(id={self.id[:8]}..., user={self.user_id[:8]}..., status={self.status})>"


# =============================================================================
# Audit Logging System (Task #95)
# =============================================================================


class AuditLogEntry(Base):
    """Tamper-evident audit log with hash chain integrity.

    Records who did what, when, and from where. Append-only entries
    linked via SHA-256 hash chain for tamper detection.
    """

    __tablename__ = "audit_log_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # Who performed the action
    actor_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    actor_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    actor_role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # What action was performed
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Where from
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Correlation
    request_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)

    # Tamper-evident hash chain
    prev_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    entry_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )

    __table_args__ = (
        Index("ix_audit_log_action_created", "action", "created_at"),
        Index("ix_audit_log_actor_created", "actor_id", "created_at"),
    )

    def compute_hash(self, previous_hash: str = "") -> str:
        """Compute SHA-256 hash for this entry linked to previous."""
        import hashlib
        import json

        payload = (
            f"{self.actor_id or ''}|{self.action}|{self.resource or ''}|"
            f"{json.dumps(self.details or {}, sort_keys=True, default=str)}|"
            f"{self.id or ''}|{previous_hash}"
        )
        return hashlib.sha256(payload.encode()).hexdigest()

    def __repr__(self) -> str:
        return (
            f"<AuditLogEntry(id={self.id[:8]}..., action={self.action}, "
            f"actor={self.actor_email or 'anonymous'})>"
        )


class SearchFeedback(Base):
    """User relevance rating for search results (Task #118)."""

    __tablename__ = "search_feedback"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    search_query: Mapped[str] = mapped_column(Text, nullable=False)
    property_id: Mapped[str] = mapped_column(String(100), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-5
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    __table_args__ = (Index("ix_search_feedback_created", "created_at"),)

    def __repr__(self) -> str:
        return f"<SearchFeedback(id={self.id[:8]}..., rating={self.rating})>"
