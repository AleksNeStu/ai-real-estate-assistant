"""
User-related repository classes.

Provides repositories for User, RefreshToken, OAuthAccount,
PasswordResetToken, EmailVerificationToken, PushSubscription,
and NotificationPreference models.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.security_utils import hash_fingerprint
from db.models import (
    EmailVerificationToken,
    NotificationPreferenceDB,
    OAuthAccount,
    PasswordResetToken,
    PushSubscription,
    RefreshToken,
    User,
)


class UserRepository:
    """Repository for User model operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        email: str,
        hashed_password: Optional[str] = None,
        full_name: Optional[str] = None,
        role: str = "user",
        is_verified: bool = False,
    ) -> User:
        """Create a new user."""
        user = User(
            id=str(uuid.uuid4()),
            email=email.lower().strip(),
            hashed_password=hashed_password,
            full_name=full_name,
            role=role,
            is_verified=is_verified,
            is_active=True,
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        result = await self.session.execute(select(User).where(User.email == email.lower().strip()))
        return result.scalar_one_or_none()

    async def update(self, user: User, **kwargs) -> User:
        """Update user fields."""
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        await self.session.flush()
        return user

    async def update_last_login(self, user: User) -> None:
        """Update user's last login timestamp."""
        user.last_login_at = datetime.now(UTC)
        await self.session.flush()

    async def set_verified(self, user: User) -> None:
        """Mark user as verified."""
        user.is_verified = True
        await self.session.flush()

    async def set_password(self, user: User, hashed_password: str) -> None:
        """Set user's password."""
        user.hashed_password = hashed_password
        await self.session.flush()

    async def delete(self, user: User) -> None:
        """Delete a user."""
        await self.session.delete(user)

    async def exists_by_email(self, email: str) -> bool:
        """Check if user exists by email."""
        result = await self.session.execute(
            select(User.id).where(User.email == email.lower().strip())
        )
        return result.scalar_one_or_none() is not None


class RefreshTokenRepository:
    """Repository for RefreshToken model operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _hash_token(token: str) -> str:
        """Hash a token for storage.

        Uses HMAC-SHA-256 with a server-side pepper. The token is high-entropy
        (cryptographically random) so the keyed hash is appropriate for
        at-rest lookups; this is NOT used for user-chosen passwords.
        """
        return hash_fingerprint(token, length=64)

    async def create(
        self,
        user_id: str,
        token: str,
        expires_days: int = 7,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> RefreshToken:
        """Create a new refresh token."""
        from uuid import uuid4

        token_hash = self._hash_token(token)
        refresh_token = RefreshToken(
            id=str(uuid4()),
            user_id=user_id,
            token_hash=token_hash,
            expires_at=datetime.now(UTC) + timedelta(days=expires_days),
            user_agent=user_agent,
            ip_address=ip_address,
        )
        self.session.add(refresh_token)
        await self.session.flush()
        return refresh_token

    async def get_by_token(self, token: str) -> Optional[RefreshToken]:
        """Get refresh token by token value."""
        token_hash = self._hash_token(token)
        result = await self.session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def revoke(self, token: RefreshToken) -> None:
        """Revoke a refresh token."""
        token.revoked_at = datetime.now(UTC)
        await self.session.flush()

    async def revoke_all_for_user(self, user_id: str) -> None:
        """Revoke all refresh tokens for a user."""
        await self.session.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
        )

    async def cleanup_expired(self, user_id: Optional[str] = None) -> int:
        """Remove expired tokens."""
        query = select(RefreshToken).where(RefreshToken.expires_at < datetime.now(UTC))
        if user_id:
            query = query.where(RefreshToken.user_id == user_id)

        result = await self.session.execute(query)
        expired_tokens = result.scalars().all()

        count = 0
        for token in expired_tokens:
            await self.session.delete(token)
            count += 1

        return count


class OAuthAccountRepository:
    """Repository for OAuthAccount model operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: str,
        provider: str,
        provider_user_id: str,
        provider_email: Optional[str] = None,
    ) -> OAuthAccount:
        """Create a new OAuth account link."""
        from uuid import uuid4

        oauth_account = OAuthAccount(
            id=str(uuid4()),
            user_id=user_id,
            provider=provider,
            provider_user_id=provider_user_id,
            provider_email=provider_email,
        )
        self.session.add(oauth_account)
        await self.session.flush()
        return oauth_account

    async def get_by_provider(self, provider: str, provider_user_id: str) -> Optional[OAuthAccount]:
        """Get OAuth account by provider and provider user ID."""
        result = await self.session.execute(
            select(OAuthAccount).where(
                OAuthAccount.provider == provider,
                OAuthAccount.provider_user_id == provider_user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_user(self, user_id: str) -> list[OAuthAccount]:
        """Get all OAuth accounts for a user."""
        result = await self.session.execute(
            select(OAuthAccount).where(OAuthAccount.user_id == user_id)
        )
        return list(result.scalars().all())

    async def delete(self, oauth_account: OAuthAccount) -> None:
        """Delete an OAuth account link."""
        await self.session.delete(oauth_account)


class PasswordResetTokenRepository:
    """Repository for PasswordResetToken model operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _hash_token(token: str) -> str:
        """Hash a token for storage.

        Uses HMAC-SHA-256 with a server-side pepper. The token is high-entropy
        (cryptographically random) so the keyed hash is appropriate for
        at-rest lookups; this is NOT used for user-chosen passwords.
        """
        return hash_fingerprint(token, length=64)

    async def create(self, user_id: str, token: str, expires_hours: int = 1) -> PasswordResetToken:
        """Create a new password reset token."""
        from uuid import uuid4

        token_hash = self._hash_token(token)
        reset_token = PasswordResetToken(
            id=str(uuid4()),
            user_id=user_id,
            token_hash=token_hash,
            expires_at=datetime.now(UTC) + timedelta(hours=expires_hours),
        )
        self.session.add(reset_token)
        await self.session.flush()
        return reset_token

    async def get_by_token(self, token: str) -> Optional[PasswordResetToken]:
        """Get password reset token by token value."""
        token_hash = self._hash_token(token)
        result = await self.session.execute(
            select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def mark_used(self, token: PasswordResetToken) -> None:
        """Mark token as used."""
        token.used_at = datetime.now(UTC)
        await self.session.flush()

    async def cleanup_expired(self) -> int:
        """Remove expired tokens."""
        result = await self.session.execute(
            select(PasswordResetToken).where(PasswordResetToken.expires_at < datetime.now(UTC))
        )
        expired_tokens = result.scalars().all()

        count = 0
        for token in expired_tokens:
            await self.session.delete(token)
            count += 1

        return count


class EmailVerificationTokenRepository:
    """Repository for EmailVerificationToken model operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _hash_token(token: str) -> str:
        """Hash a token for storage.

        Uses HMAC-SHA-256 with a server-side pepper. The token is high-entropy
        (cryptographically random) so the keyed hash is appropriate for
        at-rest lookups; this is NOT used for user-chosen passwords.
        """
        return hash_fingerprint(token, length=64)

    async def create(
        self, user_id: str, token: str, expires_hours: int = 24
    ) -> EmailVerificationToken:
        """Create a new email verification token."""
        from uuid import uuid4

        token_hash = self._hash_token(token)
        verification_token = EmailVerificationToken(
            id=str(uuid4()),
            user_id=user_id,
            token_hash=token_hash,
            expires_at=datetime.now(UTC) + timedelta(hours=expires_hours),
        )
        self.session.add(verification_token)
        await self.session.flush()
        return verification_token

    async def get_by_token(self, token: str) -> Optional[EmailVerificationToken]:
        """Get email verification token by token value."""
        token_hash = self._hash_token(token)
        result = await self.session.execute(
            select(EmailVerificationToken).where(EmailVerificationToken.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def mark_used(self, token: EmailVerificationToken) -> None:
        """Mark token as used."""
        token.used_at = datetime.now(UTC)
        await self.session.flush()

    async def invalidate_for_user(self, user_id: str) -> None:
        """Invalidate all unused tokens for a user."""
        await self.session.execute(
            update(EmailVerificationToken)
            .where(
                EmailVerificationToken.user_id == user_id,
                EmailVerificationToken.used_at.is_(None),
            )
            .values(used_at=datetime.now(UTC))
        )

    async def cleanup_expired(self) -> int:
        """Remove expired tokens."""
        result = await self.session.execute(
            select(EmailVerificationToken).where(
                EmailVerificationToken.expires_at < datetime.now(UTC)
            )
        )
        expired_tokens = result.scalars().all()

        count = 0
        for token in expired_tokens:
            await self.session.delete(token)
            count += 1

        return count


class PushSubscriptionRepository:
    """Repository for push notification subscriptions (Task #63)."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: str,
        endpoint: str,
        p256dh: str,
        auth: str,
        user_agent: Optional[str] = None,
        device_name: Optional[str] = None,
    ) -> PushSubscription:
        """Create a new push subscription."""
        from uuid import uuid4

        subscription = PushSubscription(
            id=str(uuid4()),
            user_id=user_id,
            endpoint=endpoint,
            p256dh=p256dh,
            auth=auth,
            user_agent=user_agent,
            device_name=device_name,
        )
        self.session.add(subscription)
        await self.session.flush()
        return subscription

    async def get_by_id(self, subscription_id: str) -> Optional[PushSubscription]:
        """Get subscription by ID."""
        result = await self.session.execute(
            select(PushSubscription).where(PushSubscription.id == subscription_id)
        )
        return result.scalar_one_or_none()

    async def get_by_endpoint(self, endpoint: str) -> Optional[PushSubscription]:
        """Get subscription by endpoint URL."""
        result = await self.session.execute(
            select(PushSubscription).where(PushSubscription.endpoint == endpoint)
        )
        return result.scalar_one_or_none()

    async def get_by_user(self, user_id: str, active_only: bool = True) -> list[PushSubscription]:
        """Get all subscriptions for a user."""
        query = select(PushSubscription).where(PushSubscription.user_id == user_id)
        if active_only:
            query = query.where(
                PushSubscription.is_active == True  # noqa: E712
            )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update(self, subscription: PushSubscription, **kwargs) -> PushSubscription:
        """Update subscription fields."""
        for key, value in kwargs.items():
            if hasattr(subscription, key):
                setattr(subscription, key, value)
        await self.session.flush()
        return subscription

    async def deactivate(self, subscription: PushSubscription) -> None:
        """Deactivate a subscription."""
        subscription.is_active = False
        await self.session.flush()

    async def delete(self, subscription: PushSubscription) -> None:
        """Delete a subscription."""
        await self.session.delete(subscription)

    async def delete_by_endpoint(self, endpoint: str) -> bool:
        """Delete subscription by endpoint. Returns True if deleted."""
        subscription = await self.get_by_endpoint(endpoint)
        if subscription:
            await self.session.delete(subscription)
            return True
        return False

    async def count_for_user(self, user_id: str, active_only: bool = True) -> int:
        """Count subscriptions for a user."""
        query = select(func.count(PushSubscription.id)).where(PushSubscription.user_id == user_id)
        if active_only:
            query = query.where(
                PushSubscription.is_active == True  # noqa: E712
            )
        result = await self.session.execute(query)
        return result.scalar() or 0


class NotificationPreferenceRepository:
    """Repository for NotificationPreferenceDB model operations (Task #86)."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_user_id(self, user_id: str) -> Optional[NotificationPreferenceDB]:
        """Get notification preferences for a user."""
        result = await self.session.execute(
            select(NotificationPreferenceDB).where(NotificationPreferenceDB.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_unsubscribe_token(self, token: str) -> Optional[NotificationPreferenceDB]:
        """Get notification preferences by unsubscribe token."""
        result = await self.session.execute(
            select(NotificationPreferenceDB).where(
                NotificationPreferenceDB.unsubscribe_token == token
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        user_id: str,
        price_alerts_enabled: bool = True,
        new_listings_enabled: bool = True,
        saved_search_enabled: bool = True,
        market_updates_enabled: bool = False,
        alert_frequency: str = "daily",
        email_enabled: bool = True,
        push_enabled: bool = False,
        in_app_enabled: bool = True,
        quiet_hours_start: Optional[str] = None,
        quiet_hours_end: Optional[str] = None,
        price_drop_threshold: float = 5.0,
        daily_digest_time: str = "09:00",
        weekly_digest_day: str = "monday",
        expert_mode: bool = False,
        marketing_emails: bool = False,
    ) -> NotificationPreferenceDB:
        """Create notification preferences for a user with defaults."""
        from uuid import uuid4

        prefs = NotificationPreferenceDB(
            id=str(uuid4()),
            user_id=user_id,
            price_alerts_enabled=price_alerts_enabled,
            new_listings_enabled=new_listings_enabled,
            saved_search_enabled=saved_search_enabled,
            market_updates_enabled=market_updates_enabled,
            alert_frequency=alert_frequency,
            email_enabled=email_enabled,
            push_enabled=push_enabled,
            in_app_enabled=in_app_enabled,
            quiet_hours_start=quiet_hours_start,
            quiet_hours_end=quiet_hours_end,
            price_drop_threshold=price_drop_threshold,
            daily_digest_time=daily_digest_time,
            weekly_digest_day=weekly_digest_day,
            expert_mode=expert_mode,
            marketing_emails=marketing_emails,
        )
        self.session.add(prefs)
        await self.session.flush()
        return prefs

    async def get_or_create(self, user_id: str) -> NotificationPreferenceDB:
        """Get existing preferences or create with defaults."""
        prefs = await self.get_by_user_id(user_id)
        if prefs is None:
            prefs = await self.create(user_id=user_id)
        return prefs

    async def update(self, prefs: NotificationPreferenceDB, **kwargs) -> NotificationPreferenceDB:
        """Update notification preference fields."""
        for key, value in kwargs.items():
            if hasattr(prefs, key):
                setattr(prefs, key, value)
        prefs.updated_at = datetime.now(UTC)
        await self.session.flush()
        return prefs

    async def unsubscribe_all(self, prefs: NotificationPreferenceDB) -> NotificationPreferenceDB:
        """Mark user as fully unsubscribed from all notifications."""
        prefs.unsubscribed_at = datetime.now(UTC)
        prefs.price_alerts_enabled = False
        prefs.new_listings_enabled = False
        prefs.saved_search_enabled = False
        prefs.market_updates_enabled = False
        prefs.marketing_emails = False
        prefs.email_enabled = False
        prefs.push_enabled = False
        await self.session.flush()
        return prefs

    async def unsubscribe_type(
        self, prefs: NotificationPreferenceDB, notification_type: str
    ) -> NotificationPreferenceDB:
        """Unsubscribe user from a specific notification type."""
        type_field_map = {
            "price_alerts": "price_alerts_enabled",
            "new_listings": "new_listings_enabled",
            "saved_search": "saved_search_enabled",
            "market_updates": "market_updates_enabled",
            "marketing": "marketing_emails",
        }
        field_name = type_field_map.get(notification_type)
        if field_name and hasattr(prefs, field_name):
            setattr(prefs, field_name, False)
            # Track unsubscribed types
            if prefs.unsubscribed_types is None:
                prefs.unsubscribed_types = []
            if notification_type not in prefs.unsubscribed_types:
                prefs.unsubscribed_types.append(notification_type)
        prefs.updated_at = datetime.now(UTC)
        await self.session.flush()
        return prefs

    async def delete(self, prefs: NotificationPreferenceDB) -> None:
        """Delete notification preferences (typically on user deletion)."""
        await self.session.delete(prefs)
        await self.session.flush()
