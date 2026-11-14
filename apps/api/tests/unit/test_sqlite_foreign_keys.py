"""SQLite enforces the foreign keys the schema declares.

SQLite does not enforce them by default, and the difference is not academic:
without the pragma an ON DELETE CASCADE never runs, so a child row outlives
the parent it points at. The demo's re-seed deletes every user on startup,
and the oauth_accounts links survived them - which left a sign-in that could
never finish, for every account, forever.

These tests run against the same pragma the deployments run with.
"""

import pytest
from sqlalchemy import select, text

from db.models import OAuthAccount, User


@pytest.mark.asyncio
async def test_sqlite_enforces_the_foreign_keys(db_session):
    """The pragma is on, so the schema's rules are the database's rules."""
    result = await db_session.execute(text("PRAGMA foreign_keys"))
    assert result.scalar() == 1


@pytest.mark.asyncio
async def test_deleting_a_user_takes_their_oauth_links_with_them(db_session):
    """The cascade fires - a link cannot outlive the user it points at.

    This is the demo's sign-in: the re-seed deletes every user, and the links
    used to survive them. The callback then found a link whose user was gone
    and refused the sign-in with a 500 that no visitor could get past.
    """
    user = User(id="user-1", email="cascade@example.com", is_active=True)
    db_session.add(user)
    await db_session.flush()
    db_session.add(
        OAuthAccount(
            id="oauth-1",
            user_id="user-1",
            provider="google",
            provider_user_id="google-1",
            provider_email="cascade@example.com",
        )
    )
    await db_session.flush()

    await db_session.delete(user)
    await db_session.commit()

    links = (await db_session.execute(select(OAuthAccount))).scalars().all()
    assert links == [], "the link outlived the user it pointed at"


@pytest.mark.asyncio
async def test_a_link_to_a_user_that_does_not_exist_is_refused(db_session):
    """The database refuses to write a link that points at nothing."""
    from sqlalchemy.exc import IntegrityError

    db_session.add(
        OAuthAccount(
            id="oauth-2",
            user_id="user-that-was-never-created",
            provider="google",
            provider_user_id="google-2",
            provider_email="nobody@example.com",
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()
