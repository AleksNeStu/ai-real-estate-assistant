"""The expiry of a stored token is read in the zone it was written in.

SQLite keeps no time zone. A ``DateTime(timezone=True)`` column on SQLite
stores the value as it was written - UTC - but hands it back **without** a
zone. Comparing such a value with ``datetime.now(UTC)`` raises
``TypeError: can't compare offset-naive and offset-aware datetimes``, and
the request that asked dies with a 500.

This is the shape the deployment runs on: the demo stores its users in
SQLite, so ``POST /api/v1/auth/refresh`` compared a naive value with an
aware one and answered 500 - the rotation never happened and a signed-in
visitor could not renew their session.

The same comparison sits in the password-reset and the email-verification
tokens, so the whole family is covered here.
"""

from datetime import UTC, datetime, timedelta

import pytest

from db.models import EmailVerificationToken, PasswordResetToken, RefreshToken, User
from db.user_repos import RefreshTokenRepository


def _refresh_token(expires_at: datetime, **kwargs) -> RefreshToken:
    return RefreshToken(
        id="token-1",
        user_id="user-1",
        token_hash="hash",
        expires_at=expires_at,
        **kwargs,
    )


def _password_reset_token(expires_at: datetime) -> PasswordResetToken:
    return PasswordResetToken(
        id="reset-1",
        user_id="user-1",
        token_hash="hash",
        expires_at=expires_at,
    )


def _email_verification_token(expires_at: datetime) -> EmailVerificationToken:
    return EmailVerificationToken(
        id="verify-1",
        user_id="user-1",
        token_hash="hash",
        expires_at=expires_at,
    )


class TestTheExpiryIsReadInTheZoneItWasWrittenIn:
    """A value without a zone is UTC, because UTC is what was written."""

    def test_a_refresh_token_without_a_zone_is_not_expired_while_it_is_valid(self):
        token = _refresh_token(datetime.now(UTC).replace(tzinfo=None) + timedelta(days=7))

        assert token.is_expired is False
        assert token.is_valid is True

    def test_a_refresh_token_without_a_zone_is_expired_once_it_is_past(self):
        token = _refresh_token(datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=1))

        assert token.is_expired is True
        assert token.is_valid is False

    def test_a_refresh_token_with_a_zone_is_read_the_same_way(self):
        token = _refresh_token(datetime.now(UTC) + timedelta(days=7))

        assert token.is_expired is False
        assert token.is_valid is True

    def test_a_password_reset_token_without_a_zone_does_not_raise(self):
        token = _password_reset_token(datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=1))

        assert token.is_expired is False

    def test_an_email_verification_token_without_a_zone_does_not_raise(self):
        token = _email_verification_token(
            datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=1)
        )

        assert token.is_expired is False

    def test_a_revoked_token_is_not_valid_whatever_the_expiry_says(self):
        token = _refresh_token(
            datetime.now(UTC).replace(tzinfo=None) + timedelta(days=7),
            revoked_at=datetime.now(UTC),
        )

        assert token.is_revoked is True
        assert token.is_valid is False


class TestTheRoundTripThroughSQLite:
    """The deployment's own store: written aware, read back naive."""

    @pytest.mark.asyncio
    async def test_a_token_that_went_through_the_database_is_valid(self, db_session):
        user = User(
            id="user-1",
            email="tester@example.com",
            hashed_password="hash",  # pragma: allowlist secret - a fixture value, not a credential
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()

        repo = RefreshTokenRepository(db_session)
        stored = await repo.create(
            user_id="user-1",
            token="the-token",  # pragma: allowlist secret - a fixture value, not a credential
            expires_days=7,
        )
        await db_session.commit()

        # Drop the identity map's copy: the endpoint reads the token from a
        # fresh session, so the value it sees is the one the database holds.
        db_session.expire_all()

        read_back = await repo.get_by_token("the-token")

        assert read_back is not None
        # SQLite hands the value back without a zone - that is the shape the
        # comparison used to trip over.
        assert read_back.expires_at.tzinfo is None
        assert read_back.is_expired is False
        assert read_back.is_valid is True
        assert stored.id == read_back.id
