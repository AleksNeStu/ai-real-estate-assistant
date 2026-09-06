"""
Unit tests for db/user_repos.py repository classes.

Covers: UserRepository, RefreshTokenRepository, OAuthAccountRepository,
PasswordResetTokenRepository, EmailVerificationTokenRepository,
PushSubscriptionRepository, NotificationPreferenceRepository.
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core.security_utils import hash_fingerprint
from db.models import (
    User,
)
from db.user_repos import (
    EmailVerificationTokenRepository,
    NotificationPreferenceRepository,
    OAuthAccountRepository,
    PasswordResetTokenRepository,
    PushSubscriptionRepository,
    RefreshTokenRepository,
    UserRepository,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _hash(token: str) -> str:
    # Production uses HMAC-SHA-256 with a server-side pepper (see
    # core.security_utils.hash_fingerprint). Mirror that here so the
    # token_hash column matches what the repository actually writes.
    return hash_fingerprint(token, length=64)


# ===========================================================================
# UserRepository
# ===========================================================================


class TestUserRepository:
    """Tests for UserRepository."""

    @pytest.fixture
    def repo(self, db_session: AsyncSession) -> UserRepository:
        return UserRepository(db_session)

    async def _create_user(
        self, repo: UserRepository, email: str = "alice@example.com", **kwargs
    ) -> User:
        return await repo.create(email=email, **kwargs)

    # -- create --

    async def test_create_basic(self, repo: UserRepository):
        user = await self._create_user(repo)
        assert user.id is not None
        assert user.email == "alice@example.com"
        assert user.is_active is True
        assert user.is_verified is False
        assert user.role == "user"
        assert user.hashed_password is None
        assert user.full_name is None

    async def test_create_with_all_fields(self, repo: UserRepository):
        user = await repo.create(
            email="Bob@Example.COM  ",
            hashed_password="secret",
            full_name="Bob Smith",
            role="admin",
            is_verified=True,
        )
        assert user.email == "bob@example.com"
        assert user.hashed_password == "secret"
        assert user.full_name == "Bob Smith"
        assert user.role == "admin"
        assert user.is_verified is True

    async def test_create_normalizes_email(self, repo: UserRepository):
        user = await repo.create(email="  UPPER@CASE.COM  ")
        assert user.email == "upper@case.com"

    # -- get_by_id --

    async def test_get_by_id_found(self, repo: UserRepository):
        created = await self._create_user(repo)
        found = await repo.get_by_id(created.id)
        assert found is not None
        assert found.id == created.id

    async def test_get_by_id_not_found(self, repo: UserRepository):
        found = await repo.get_by_id("nonexistent-id")
        assert found is None

    # -- get_by_email --

    async def test_get_by_email_found(self, repo: UserRepository):
        created = await self._create_user(repo, email="find@me.com")
        found = await repo.get_by_email("find@me.com")
        assert found is not None
        assert found.id == created.id

    async def test_get_by_email_normalizes(self, repo: UserRepository):
        created = await self._create_user(repo, email="norm@test.com")
        found = await repo.get_by_email("  NORM@TEST.COM  ")
        assert found is not None
        assert found.id == created.id

    async def test_get_by_email_not_found(self, repo: UserRepository):
        found = await repo.get_by_email("nobody@test.com")
        assert found is None

    # -- update --

    async def test_update_sets_fields(self, repo: UserRepository):
        user = await self._create_user(repo)
        updated = await repo.update(user, full_name="New Name", role="editor")
        assert updated.full_name == "New Name"
        assert updated.role == "editor"

    async def test_update_ignores_invalid_fields(self, repo: UserRepository):
        user = await self._create_user(repo)
        updated = await repo.update(user, nonexistent_field="value", full_name="Valid")
        assert updated.full_name == "Valid"
        assert not hasattr(updated, "nonexistent_field")

    # -- update_last_login --

    async def test_update_last_login(self, repo: UserRepository):
        user = await self._create_user(repo)
        assert user.last_login_at is None
        await repo.update_last_login(user)
        assert user.last_login_at is not None

    # -- set_verified --

    async def test_set_verified(self, repo: UserRepository):
        user = await self._create_user(repo, is_verified=False)
        assert user.is_verified is False
        await repo.set_verified(user)
        assert user.is_verified is True

    # -- set_password --

    async def test_set_password(self, repo: UserRepository):
        user = await self._create_user(repo)
        assert user.hashed_password is None
        await repo.set_password(user, "hashed_new_pw")
        assert user.hashed_password == "hashed_new_pw"

    # -- delete --

    async def test_delete(self, repo: UserRepository, db_session: AsyncSession):
        user = await self._create_user(repo, email="delete@me.com")
        uid = user.id
        await repo.delete(user)
        await db_session.flush()
        found = await repo.get_by_id(uid)
        assert found is None

    # -- exists_by_email --

    async def test_exists_by_email_true(self, repo: UserRepository):
        await self._create_user(repo, email="exists@test.com")
        assert await repo.exists_by_email("exists@test.com") is True

    async def test_exists_by_email_false(self, repo: UserRepository):
        assert await repo.exists_by_email("nope@test.com") is False

    async def test_exists_by_email_normalizes(self, repo: UserRepository):
        await self._create_user(repo, email="norm2@test.com")
        assert await repo.exists_by_email("  NORM2@TEST.COM  ") is True


# ===========================================================================
# RefreshTokenRepository
# ===========================================================================


class TestRefreshTokenRepository:
    """Tests for RefreshTokenRepository."""

    @pytest.fixture
    def repo(self, db_session: AsyncSession) -> RefreshTokenRepository:
        return RefreshTokenRepository(db_session)

    @pytest.fixture
    async def user(self, db_session: AsyncSession) -> User:
        repo = UserRepository(db_session)
        return await repo.create(email="rt-user@test.com")

    # -- _hash_token (static) --

    def test_hash_token(self):
        token = "my-refresh-token"
        result = RefreshTokenRepository._hash_token(token)
        assert result == hash_fingerprint(token, length=64)

    # -- create --

    async def test_create_basic(self, repo: RefreshTokenRepository, user: User):
        rt = await repo.create(user_id=user.id, token="token-abc")
        assert rt.id is not None
        assert rt.user_id == user.id
        assert rt.token_hash == _hash("token-abc")
        assert rt.expires_at > datetime.now(UTC)
        assert rt.user_agent is None
        assert rt.ip_address is None

    async def test_create_with_metadata(self, repo: RefreshTokenRepository, user: User):
        rt = await repo.create(
            user_id=user.id,
            token="tok",
            expires_days=14,
            user_agent="Mozilla/5.0",
            ip_address="192.168.1.1",
        )
        assert rt.user_agent == "Mozilla/5.0"
        assert rt.ip_address == "192.168.1.1"
        expected_exp = datetime.now(UTC) + timedelta(days=14)
        assert abs((rt.expires_at - expected_exp).total_seconds()) < 5

    # -- get_by_token --

    async def test_get_by_token_found(self, repo: RefreshTokenRepository, user: User):
        await repo.create(user_id=user.id, token="find-me")
        found = await repo.get_by_token("find-me")
        assert found is not None
        assert found.user_id == user.id

    async def test_get_by_token_not_found(self, repo: RefreshTokenRepository):
        found = await repo.get_by_token("does-not-exist")
        assert found is None

    # -- revoke --

    async def test_revoke(self, repo: RefreshTokenRepository, user: User):
        rt = await repo.create(user_id=user.id, token="revoke-me")
        assert rt.revoked_at is None
        await repo.revoke(rt)
        assert rt.revoked_at is not None

    # -- revoke_all_for_user --

    async def test_revoke_all_for_user(
        self, repo: RefreshTokenRepository, user: User, db_session: AsyncSession
    ):
        await repo.create(user_id=user.id, token="t1")
        await repo.create(user_id=user.id, token="t2")
        await repo.revoke_all_for_user(user.id)
        await db_session.flush()
        found1 = await repo.get_by_token("t1")
        found2 = await repo.get_by_token("t2")
        assert found1.revoked_at is not None
        assert found2.revoked_at is not None

    # -- cleanup_expired --

    async def test_cleanup_expired_removes_tokens(
        self, repo: RefreshTokenRepository, user: User, db_session: AsyncSession
    ):
        rt = await repo.create(user_id=user.id, token="expired", expires_days=0)
        # Force expiration
        rt.expires_at = datetime.now(UTC) - timedelta(hours=1)
        await db_session.flush()

        count = await repo.cleanup_expired()
        assert count == 1
        # Flush pending deletes and expire cache so deleted objects are gone
        await db_session.flush()
        db_session.expire_all()
        found = await repo.get_by_token("expired")
        assert found is None

    async def test_cleanup_expired_filters_by_user(self, db_session: AsyncSession):
        user_repo = UserRepository(db_session)
        user_a = await user_repo.create(email="a-exp@test.com")
        user_b = await user_repo.create(email="b-exp@test.com")

        rt_repo = RefreshTokenRepository(db_session)
        rt_a = await rt_repo.create(user_id=user_a.id, token="a-exp", expires_days=0)
        rt_b = await rt_repo.create(user_id=user_b.id, token="b-exp", expires_days=0)
        rt_a.expires_at = datetime.now(UTC) - timedelta(hours=1)
        rt_b.expires_at = datetime.now(UTC) - timedelta(hours=1)
        await db_session.flush()

        count = await rt_repo.cleanup_expired(user_id=user_a.id)
        assert count == 1
        await db_session.flush()
        db_session.expire_all()
        assert await rt_repo.get_by_token("a-exp") is None
        assert await rt_repo.get_by_token("b-exp") is not None

    async def test_cleanup_expired_none_when_no_expired(
        self, repo: RefreshTokenRepository, user: User
    ):
        await repo.create(user_id=user.id, token="valid-token", expires_days=30)
        count = await repo.cleanup_expired()
        assert count == 0


# ===========================================================================
# OAuthAccountRepository
# ===========================================================================


class TestOAuthAccountRepository:
    """Tests for OAuthAccountRepository."""

    @pytest.fixture
    def repo(self, db_session: AsyncSession) -> OAuthAccountRepository:
        return OAuthAccountRepository(db_session)

    @pytest.fixture
    async def user(self, db_session: AsyncSession) -> User:
        return await UserRepository(db_session).create(email="oauth-user@test.com")

    # -- create --

    async def test_create_basic(self, repo: OAuthAccountRepository, user: User):
        oa = await repo.create(user_id=user.id, provider="google", provider_user_id="g-123")
        assert oa.id is not None
        assert oa.user_id == user.id
        assert oa.provider == "google"
        assert oa.provider_user_id == "g-123"
        assert oa.provider_email is None

    async def test_create_with_email(self, repo: OAuthAccountRepository, user: User):
        oa = await repo.create(
            user_id=user.id,
            provider="apple",
            provider_user_id="a-456",
            provider_email="user@icloud.com",
        )
        assert oa.provider_email == "user@icloud.com"

    # -- get_by_provider --

    async def test_get_by_provider_found(self, repo: OAuthAccountRepository, user: User):
        await repo.create(user_id=user.id, provider="github", provider_user_id="gh-1")
        found = await repo.get_by_provider("github", "gh-1")
        assert found is not None
        assert found.provider == "github"

    async def test_get_by_provider_not_found(self, repo: OAuthAccountRepository):
        found = await repo.get_by_provider("github", "missing")
        assert found is None

    # -- get_by_user --

    async def test_get_by_user(self, repo: OAuthAccountRepository, user: User):
        await repo.create(user_id=user.id, provider="google", provider_user_id="g1")
        await repo.create(user_id=user.id, provider="github", provider_user_id="gh1")
        accounts = await repo.get_by_user(user.id)
        assert len(accounts) == 2

    async def test_get_by_user_empty(self, repo: OAuthAccountRepository):
        accounts = await repo.get_by_user("nonexistent-user")
        assert accounts == []

    # -- delete --

    async def test_delete(self, repo: OAuthAccountRepository, user: User, db_session: AsyncSession):
        oa = await repo.create(user_id=user.id, provider="google", provider_user_id="del-me")
        await repo.delete(oa)
        await db_session.flush()
        found = await repo.get_by_provider("google", "del-me")
        assert found is None


# ===========================================================================
# PasswordResetTokenRepository
# ===========================================================================


class TestPasswordResetTokenRepository:
    """Tests for PasswordResetTokenRepository."""

    @pytest.fixture
    def repo(self, db_session: AsyncSession) -> PasswordResetTokenRepository:
        return PasswordResetTokenRepository(db_session)

    @pytest.fixture
    async def user(self, db_session: AsyncSession) -> User:
        return await UserRepository(db_session).create(email="pr-user@test.com")

    # -- _hash_token --

    def test_hash_token(self):
        assert PasswordResetTokenRepository._hash_token("abc") == _hash("abc")

    # -- create --

    async def test_create(self, repo: PasswordResetTokenRepository, user: User):
        prt = await repo.create(user_id=user.id, token="reset-tok")
        assert prt.id is not None
        assert prt.user_id == user.id
        assert prt.token_hash == _hash("reset-tok")
        assert prt.expires_at > datetime.now(UTC)

    async def test_create_custom_expiry(self, repo: PasswordResetTokenRepository, user: User):
        prt = await repo.create(user_id=user.id, token="tok", expires_hours=2)
        expected = datetime.now(UTC) + timedelta(hours=2)
        assert abs((prt.expires_at - expected).total_seconds()) < 5

    # -- get_by_token --

    async def test_get_by_token_found(self, repo: PasswordResetTokenRepository, user: User):
        await repo.create(user_id=user.id, token="find-reset")
        found = await repo.get_by_token("find-reset")
        assert found is not None
        assert found.user_id == user.id

    async def test_get_by_token_not_found(self, repo: PasswordResetTokenRepository):
        found = await repo.get_by_token("missing")
        assert found is None

    # -- mark_used --

    async def test_mark_used(self, repo: PasswordResetTokenRepository, user: User):
        prt = await repo.create(user_id=user.id, token="use-me")
        assert prt.used_at is None
        await repo.mark_used(prt)
        assert prt.used_at is not None

    # -- cleanup_expired --

    async def test_cleanup_expired(
        self, repo: PasswordResetTokenRepository, user: User, db_session: AsyncSession
    ):
        prt = await repo.create(user_id=user.id, token="expired-reset", expires_hours=0)
        prt.expires_at = datetime.now(UTC) - timedelta(hours=1)
        await db_session.flush()

        count = await repo.cleanup_expired()
        assert count == 1
        await db_session.flush()
        db_session.expire_all()
        assert await repo.get_by_token("expired-reset") is None

    async def test_cleanup_expired_none(self, repo: PasswordResetTokenRepository, user: User):
        await repo.create(user_id=user.id, token="valid-reset", expires_hours=24)
        count = await repo.cleanup_expired()
        assert count == 0


# ===========================================================================
# EmailVerificationTokenRepository
# ===========================================================================


class TestEmailVerificationTokenRepository:
    """Tests for EmailVerificationTokenRepository."""

    @pytest.fixture
    def repo(self, db_session: AsyncSession) -> EmailVerificationTokenRepository:
        return EmailVerificationTokenRepository(db_session)

    @pytest.fixture
    async def user(self, db_session: AsyncSession) -> User:
        return await UserRepository(db_session).create(email="ev-user@test.com")

    # -- _hash_token --

    def test_hash_token(self):
        assert EmailVerificationTokenRepository._hash_token("x") == _hash("x")

    # -- create --

    async def test_create(self, repo: EmailVerificationTokenRepository, user: User):
        evt = await repo.create(user_id=user.id, token="verify-tok")
        assert evt.id is not None
        assert evt.user_id == user.id
        assert evt.token_hash == _hash("verify-tok")
        assert evt.expires_at > datetime.now(UTC)

    async def test_create_custom_expiry(self, repo: EmailVerificationTokenRepository, user: User):
        evt = await repo.create(user_id=user.id, token="tok", expires_hours=48)
        expected = datetime.now(UTC) + timedelta(hours=48)
        assert abs((evt.expires_at - expected).total_seconds()) < 5

    # -- get_by_token --

    async def test_get_by_token_found(self, repo: EmailVerificationTokenRepository, user: User):
        await repo.create(user_id=user.id, token="find-verify")
        found = await repo.get_by_token("find-verify")
        assert found is not None
        assert found.user_id == user.id

    async def test_get_by_token_not_found(self, repo: EmailVerificationTokenRepository):
        found = await repo.get_by_token("nope")
        assert found is None

    # -- mark_used --

    async def test_mark_used(self, repo: EmailVerificationTokenRepository, user: User):
        evt = await repo.create(user_id=user.id, token="use-verify")
        assert evt.used_at is None
        await repo.mark_used(evt)
        assert evt.used_at is not None

    # -- invalidate_for_user --

    async def test_invalidate_for_user(
        self, repo: EmailVerificationTokenRepository, user: User, db_session: AsyncSession
    ):
        await repo.create(user_id=user.id, token="v1")
        await repo.create(user_id=user.id, token="v2")
        await repo.invalidate_for_user(user.id)
        await db_session.flush()

        found1 = await repo.get_by_token("v1")
        found2 = await repo.get_by_token("v2")
        assert found1.used_at is not None
        assert found2.used_at is not None

    # -- cleanup_expired --

    async def test_cleanup_expired(
        self, repo: EmailVerificationTokenRepository, user: User, db_session: AsyncSession
    ):
        evt = await repo.create(user_id=user.id, token="expired-v", expires_hours=0)
        evt.expires_at = datetime.now(UTC) - timedelta(hours=1)
        await db_session.flush()

        count = await repo.cleanup_expired()
        assert count == 1
        await db_session.flush()
        db_session.expire_all()
        assert await repo.get_by_token("expired-v") is None

    async def test_cleanup_expired_none(self, repo: EmailVerificationTokenRepository, user: User):
        await repo.create(user_id=user.id, token="valid-v", expires_hours=24)
        count = await repo.cleanup_expired()
        assert count == 0


# ===========================================================================
# PushSubscriptionRepository
# ===========================================================================


class TestPushSubscriptionRepository:
    """Tests for PushSubscriptionRepository."""

    @pytest.fixture
    def repo(self, db_session: AsyncSession) -> PushSubscriptionRepository:
        return PushSubscriptionRepository(db_session)

    @pytest.fixture
    async def user(self, db_session: AsyncSession) -> User:
        return await UserRepository(db_session).create(email="push-user@test.com")

    # -- create --

    async def test_create_basic(self, repo: PushSubscriptionRepository, user: User):
        sub = await repo.create(
            user_id=user.id,
            endpoint="https://push.example.com/123",
            p256dh="key123",
            auth="auth456",
        )
        assert sub.id is not None
        assert sub.user_id == user.id
        assert sub.endpoint == "https://push.example.com/123"
        assert sub.p256dh == "key123"
        assert sub.auth == "auth456"
        assert sub.user_agent is None
        assert sub.device_name is None
        assert sub.is_active is True

    async def test_create_with_metadata(self, repo: PushSubscriptionRepository, user: User):
        sub = await repo.create(
            user_id=user.id,
            endpoint="https://push.example.com/456",
            p256dh="k",
            auth="a",
            user_agent="Chrome/120",
            device_name="Chrome on Windows",
        )
        assert sub.user_agent == "Chrome/120"
        assert sub.device_name == "Chrome on Windows"

    # -- get_by_id --

    async def test_get_by_id_found(self, repo: PushSubscriptionRepository, user: User):
        sub = await repo.create(user_id=user.id, endpoint="https://p.co/1", p256dh="k", auth="a")
        found = await repo.get_by_id(sub.id)
        assert found is not None
        assert found.id == sub.id

    async def test_get_by_id_not_found(self, repo: PushSubscriptionRepository):
        found = await repo.get_by_id("nonexistent")
        assert found is None

    # -- get_by_endpoint --

    async def test_get_by_endpoint_found(self, repo: PushSubscriptionRepository, user: User):
        await repo.create(user_id=user.id, endpoint="https://p.co/ep1", p256dh="k", auth="a")
        found = await repo.get_by_endpoint("https://p.co/ep1")
        assert found is not None
        assert found.endpoint == "https://p.co/ep1"

    async def test_get_by_endpoint_not_found(self, repo: PushSubscriptionRepository):
        found = await repo.get_by_endpoint("https://p.co/missing")
        assert found is None

    # -- get_by_user --

    async def test_get_by_user_active_only(
        self, repo: PushSubscriptionRepository, user: User, db_session: AsyncSession
    ):
        await repo.create(user_id=user.id, endpoint="https://p.co/a1", p256dh="k", auth="a")
        sub2 = await repo.create(
            user_id=user.id, endpoint="https://p.co/a2", p256dh="k2", auth="a2"
        )
        sub2.is_active = False
        await db_session.flush()
        subs = await repo.get_by_user(user.id, active_only=True)
        assert len(subs) == 1
        assert subs[0].endpoint == "https://p.co/a1"

    async def test_get_by_user_all(
        self, repo: PushSubscriptionRepository, user: User, db_session: AsyncSession
    ):
        await repo.create(user_id=user.id, endpoint="https://p.co/b1", p256dh="k", auth="a")
        sub2 = await repo.create(
            user_id=user.id, endpoint="https://p.co/b2", p256dh="k2", auth="a2"
        )
        sub2.is_active = False
        await db_session.flush()
        subs = await repo.get_by_user(user.id, active_only=False)
        assert len(subs) == 2

    # -- update --

    async def test_update(self, repo: PushSubscriptionRepository, user: User):
        sub = await repo.create(user_id=user.id, endpoint="https://p.co/u", p256dh="k", auth="a")
        updated = await repo.update(sub, device_name="New Device")
        assert updated.device_name == "New Device"

    async def test_update_ignores_invalid(self, repo: PushSubscriptionRepository, user: User):
        sub = await repo.create(user_id=user.id, endpoint="https://p.co/u2", p256dh="k", auth="a")
        updated = await repo.update(sub, bad_field="x", device_name="Ok")
        assert updated.device_name == "Ok"
        assert not hasattr(updated, "bad_field")

    # -- deactivate --

    async def test_deactivate(self, repo: PushSubscriptionRepository, user: User):
        sub = await repo.create(user_id=user.id, endpoint="https://p.co/d", p256dh="k", auth="a")
        assert sub.is_active is True
        await repo.deactivate(sub)
        assert sub.is_active is False

    # -- delete --

    async def test_delete(
        self, repo: PushSubscriptionRepository, user: User, db_session: AsyncSession
    ):
        sub = await repo.create(user_id=user.id, endpoint="https://p.co/del", p256dh="k", auth="a")
        await repo.delete(sub)
        await db_session.flush()
        found = await repo.get_by_endpoint("https://p.co/del")
        assert found is None

    # -- delete_by_endpoint --

    async def test_delete_by_endpoint_found(
        self, repo: PushSubscriptionRepository, user: User, db_session: AsyncSession
    ):
        await repo.create(user_id=user.id, endpoint="https://p.co/dbe", p256dh="k", auth="a")
        result = await repo.delete_by_endpoint("https://p.co/dbe")
        assert result is True
        await db_session.flush()
        found = await repo.get_by_endpoint("https://p.co/dbe")
        assert found is None

    async def test_delete_by_endpoint_not_found(self, repo: PushSubscriptionRepository):
        result = await repo.delete_by_endpoint("https://p.co/missing")
        assert result is False

    # -- count_for_user --

    async def test_count_for_user_active(
        self, repo: PushSubscriptionRepository, user: User, db_session: AsyncSession
    ):
        await repo.create(user_id=user.id, endpoint="https://p.co/c1", p256dh="k", auth="a")
        await repo.create(user_id=user.id, endpoint="https://p.co/c2", p256dh="k2", auth="a2")
        sub3 = await repo.create(
            user_id=user.id, endpoint="https://p.co/c3", p256dh="k3", auth="a3"
        )
        sub3.is_active = False
        await db_session.flush()
        count = await repo.count_for_user(user.id, active_only=True)
        assert count == 2

    async def test_count_for_user_all(self, repo: PushSubscriptionRepository, user: User):
        await repo.create(user_id=user.id, endpoint="https://p.co/c4", p256dh="k", auth="a")
        await repo.create(user_id=user.id, endpoint="https://p.co/c5", p256dh="k2", auth="a2")
        count = await repo.count_for_user(user.id, active_only=False)
        assert count == 2

    async def test_count_for_user_zero(self, repo: PushSubscriptionRepository):
        count = await repo.count_for_user("nonexistent")
        assert count == 0


# ===========================================================================
# NotificationPreferenceRepository
# ===========================================================================


class TestNotificationPreferenceRepository:
    """Tests for NotificationPreferenceRepository."""

    @pytest.fixture
    def repo(self, db_session: AsyncSession) -> NotificationPreferenceRepository:
        return NotificationPreferenceRepository(db_session)

    @pytest.fixture
    async def user(self, db_session: AsyncSession) -> User:
        return await UserRepository(db_session).create(email="notif-user@test.com")

    # -- create --

    async def test_create_defaults(self, repo: NotificationPreferenceRepository, user: User):
        prefs = await repo.create(user_id=user.id)
        assert prefs.id is not None
        assert prefs.user_id == user.id
        assert prefs.price_alerts_enabled is True
        assert prefs.new_listings_enabled is True
        assert prefs.saved_search_enabled is True
        assert prefs.market_updates_enabled is False
        assert prefs.alert_frequency == "daily"
        assert prefs.email_enabled is True
        assert prefs.push_enabled is False
        assert prefs.in_app_enabled is True
        assert prefs.quiet_hours_start is None
        assert prefs.quiet_hours_end is None
        assert prefs.price_drop_threshold == 5.0
        assert prefs.daily_digest_time == "09:00"
        assert prefs.weekly_digest_day == "monday"
        assert prefs.expert_mode is False
        assert prefs.marketing_emails is False

    async def test_create_custom(self, repo: NotificationPreferenceRepository, user: User):
        prefs = await repo.create(
            user_id=user.id,
            price_alerts_enabled=False,
            alert_frequency="weekly",
            push_enabled=True,
            quiet_hours_start="22:00",
            quiet_hours_end="08:00",
            price_drop_threshold=10.0,
            expert_mode=True,
            marketing_emails=True,
        )
        assert prefs.price_alerts_enabled is False
        assert prefs.alert_frequency == "weekly"
        assert prefs.push_enabled is True
        assert prefs.quiet_hours_start == "22:00"
        assert prefs.quiet_hours_end == "08:00"
        assert prefs.price_drop_threshold == 10.0
        assert prefs.expert_mode is True
        assert prefs.marketing_emails is True

    # -- get_by_user_id --

    async def test_get_by_user_id_found(self, repo: NotificationPreferenceRepository, user: User):
        await repo.create(user_id=user.id)
        found = await repo.get_by_user_id(user.id)
        assert found is not None
        assert found.user_id == user.id

    async def test_get_by_user_id_not_found(
        self,
        repo: NotificationPreferenceRepository,
    ):
        found = await repo.get_by_user_id("nonexistent")
        assert found is None

    # -- get_by_unsubscribe_token --

    async def test_get_by_unsubscribe_token(
        self, repo: NotificationPreferenceRepository, user: User
    ):
        prefs = await repo.create(user_id=user.id)
        found = await repo.get_by_unsubscribe_token(prefs.unsubscribe_token)
        assert found is not None
        assert found.id == prefs.id

    async def test_get_by_unsubscribe_token_not_found(
        self,
        repo: NotificationPreferenceRepository,
    ):
        found = await repo.get_by_unsubscribe_token("bad-token")
        assert found is None

    # -- get_or_create --

    async def test_get_or_create_creates_new(
        self, repo: NotificationPreferenceRepository, user: User
    ):
        prefs = await repo.get_or_create(user.id)
        assert prefs is not None
        assert prefs.user_id == user.id

    async def test_get_or_create_returns_existing(
        self, repo: NotificationPreferenceRepository, user: User
    ):
        created = await repo.create(user_id=user.id)
        found = await repo.get_or_create(user.id)
        assert found.id == created.id

    # -- update --

    async def test_update_fields(self, repo: NotificationPreferenceRepository, user: User):
        prefs = await repo.create(user_id=user.id)
        updated = await repo.update(prefs, alert_frequency="instant", push_enabled=True)
        assert updated.alert_frequency == "instant"
        assert updated.push_enabled is True
        assert updated.updated_at is not None

    async def test_update_ignores_invalid(self, repo: NotificationPreferenceRepository, user: User):
        prefs = await repo.create(user_id=user.id)
        updated = await repo.update(prefs, bad_field="x")
        assert not hasattr(updated, "bad_field")

    # -- unsubscribe_all --

    async def test_unsubscribe_all(self, repo: NotificationPreferenceRepository, user: User):
        prefs = await repo.create(user_id=user.id)
        result = await repo.unsubscribe_all(prefs)
        assert result.unsubscribed_at is not None
        assert result.price_alerts_enabled is False
        assert result.new_listings_enabled is False
        assert result.saved_search_enabled is False
        assert result.market_updates_enabled is False
        assert result.marketing_emails is False
        assert result.email_enabled is False
        assert result.push_enabled is False

    # -- unsubscribe_type --

    async def test_unsubscribe_type_known(self, repo: NotificationPreferenceRepository, user: User):
        prefs = await repo.create(user_id=user.id)
        result = await repo.unsubscribe_type(prefs, "price_alerts")
        assert result.price_alerts_enabled is False
        assert "price_alerts" in result.unsubscribed_types

    async def test_unsubscribe_type_marketing(
        self, repo: NotificationPreferenceRepository, user: User
    ):
        prefs = await repo.create(user_id=user.id, marketing_emails=True)
        assert prefs.marketing_emails is True
        result = await repo.unsubscribe_type(prefs, "marketing")
        assert result.marketing_emails is False
        assert "marketing" in result.unsubscribed_types

    async def test_unsubscribe_type_unknown_ignored(
        self, repo: NotificationPreferenceRepository, user: User
    ):
        prefs = await repo.create(user_id=user.id)
        result = await repo.unsubscribe_type(prefs, "nonexistent_type")
        # Should not crash; unsubscribed_types may remain None or empty
        assert result.updated_at is not None

    async def test_unsubscribe_type_no_duplicates(
        self, repo: NotificationPreferenceRepository, user: User
    ):
        prefs = await repo.create(user_id=user.id)
        await repo.unsubscribe_type(prefs, "price_alerts")
        await repo.unsubscribe_type(prefs, "price_alerts")
        assert prefs.unsubscribed_types.count("price_alerts") == 1

    # -- delete --

    async def test_delete(
        self, repo: NotificationPreferenceRepository, user: User, db_session: AsyncSession
    ):
        prefs = await repo.create(user_id=user.id)
        await repo.delete(prefs)
        await db_session.flush()
        found = await repo.get_by_user_id(user.id)
        assert found is None
