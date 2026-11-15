"""Lead scoring models for real estate lead prioritization (Task #113).

Supplements the main Lead/LeadScore models in db/models.py with
domain-specific models for budget-fit analysis and urgency scoring.
"""

from datetime import UTC, datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.database import Base
from db.models import Lead  # noqa: F401


class LeadPriorityScore(Base):
    """Lead priority score for agency lead prioritization.

    Stores the composite prioritization score that combines:
    - budget_fit: how well the lead's budget matches available properties
    - urgency: how time-sensitive the lead's needs are
    - engagement: how actively the lead interacts with the platform
    """

    __tablename__ = "lead_priority_scores"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    lead_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    property_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    # Composite score (0-100)
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Component scores (0-100 each)
    budget_fit: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    urgency: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    engagement: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Source tracking
    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    lead: Mapped["Lead"] = relationship("Lead", backref="priority_scores")  # noqa: F821

    __table_args__ = (
        Index("ix_lead_priority_lead_created", "lead_id", "created_at"),
        Index("ix_lead_priority_agent_score", "agent_id", "score"),
    )

    def __repr__(self) -> str:
        return (
            f"<LeadPriorityScore(id={self.id[:8]}..., "
            f"score={self.score:.1f}, budget_fit={self.budget_fit:.1f}, "
            f"urgency={self.urgency:.1f})>"
        )
