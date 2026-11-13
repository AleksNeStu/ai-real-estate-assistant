"""
Repository pattern for database operations.

Backward-compatible re-export shim. All repository classes have been
decomposed into domain-focused modules:

  - db.user_repos       -> User, RefreshToken, OAuthAccount, PasswordReset,
                           EmailVerification, PushSubscription,
                           NotificationPreference
  - db.search_repos     -> SavedSearch, Collection, Favorite, FilterPreset
  - db.lead_repos       -> Lead, LeadInteraction, LeadScore, AgentAssignment
  - db.analytics_repos  -> PriceSnapshot, Anomaly, CMAReport, AuditLog
  - db.agent_repos      -> AgentProfile, AgentListing, AgentInquiry,
                           ViewingAppointment
  - db.document_repos   -> Document, DocumentTemplate, SignatureRequest,
                           SignedDocument
  - db.buyer_memory_repo -> BuyerMemoryFact
"""

from db.agent_repos import (  # noqa: F401
    AgentInquiryRepository,
    AgentListingRepository,
    AgentProfileRepository,
    ViewingAppointmentRepository,
)
from db.analytics_repos import (  # noqa: F401
    AnomalyRepository,
    AuditLogRepository,
    CMAReportRepository,
    PriceSnapshotRepository,
)
from db.buyer_memory_repo import (  # noqa: F401
    BuyerMemoryRepository,
)
from db.document_repos import (  # noqa: F401
    DocumentRepository,
    DocumentTemplateRepository,
    SignatureRequestRepository,
    SignedDocumentRepository,
)
from db.lead_repos import (  # noqa: F401
    AgentAssignmentRepository,
    LeadInteractionRepository,
    LeadRepository,
    LeadScoreRepository,
)
from db.search_repos import (  # noqa: F401
    CollectionRepository,
    FavoriteRepository,
    FilterPresetRepository,
    SavedSearchRepository,
)
from db.user_repos import (  # noqa: F401
    EmailVerificationTokenRepository,
    NotificationPreferenceRepository,
    OAuthAccountRepository,
    PasswordResetTokenRepository,
    PushSubscriptionRepository,
    RefreshTokenRepository,
    UserRepository,
)

__all__ = [
    # Agent
    "AgentProfileRepository",
    "AgentListingRepository",
    "AgentInquiryRepository",
    "ViewingAppointmentRepository",
    # Analytics
    "PriceSnapshotRepository",
    "AnomalyRepository",
    "CMAReportRepository",
    "AuditLogRepository",
    # Document
    "DocumentRepository",
    "DocumentTemplateRepository",
    "SignatureRequestRepository",
    "SignedDocumentRepository",
    # Lead
    "LeadRepository",
    "LeadInteractionRepository",
    "LeadScoreRepository",
    "AgentAssignmentRepository",
    # Search
    "SavedSearchRepository",
    "CollectionRepository",
    "FavoriteRepository",
    "FilterPresetRepository",
    # User
    "UserRepository",
    "RefreshTokenRepository",
    "OAuthAccountRepository",
    "PasswordResetTokenRepository",
    "EmailVerificationTokenRepository",
    "PushSubscriptionRepository",
    "NotificationPreferenceRepository",
    # Buyer Memory
    "BuyerMemoryRepository",
]
