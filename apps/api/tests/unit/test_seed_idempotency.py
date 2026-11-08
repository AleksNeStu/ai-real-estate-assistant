"""The start-up seed has to be idempotent (Task #38).

The seed runs on every start of the demo. Before the fix, the notification
preferences were looked up by the primary key of the row - which is a fresh
UUID - while the row stores the *user* id in its own column. The lookup
therefore never found anything, every start inserted a second row for the
same user, the unique constraint on ``user_id`` fired and the seed aborted
right there: the rest of the seed never ran and the next start failed the
same way.
"""

import pytest
from sqlalchemy import func, select

from alembic.seed import (
    _seed_notification_preferences,
    _seed_saved_searches,
    _seed_users,
)
from db.models import NotificationPreferenceDB, SavedSearchDB, User

pytestmark = pytest.mark.asyncio


async def _make_user(session, user_id: str = "user-seed-001") -> User:
    user = User(
        id=user_id,
        email=f"{user_id}@example.com",
        hashed_password="x",
        is_active=True,
        is_verified=True,
        role="user",
    )
    session.add(user)
    await session.commit()
    return user


async def test_notification_preferences_are_created_once(db_session):
    """Running the seed twice must not raise and must not duplicate the row."""
    user = await _make_user(db_session)

    await _seed_notification_preferences(db_session, [user])
    await db_session.commit()

    await _seed_notification_preferences(db_session, [user])
    await db_session.commit()

    count = await db_session.scalar(
        select(func.count())
        .select_from(NotificationPreferenceDB)
        .where(NotificationPreferenceDB.user_id == user.id)
    )
    assert count == 1


async def test_notification_preferences_survive_a_broken_row(db_session):
    """One row that cannot be written must not cost the remaining users."""
    first = await _make_user(db_session, "user-seed-001")
    second = await _make_user(db_session, "user-seed-002")

    real_flush = db_session.flush
    calls = {"n": 0}

    async def failing_flush(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("simulated write failure")
        return await real_flush(*args, **kwargs)

    db_session.flush = failing_flush  # type: ignore[method-assign]

    await _seed_notification_preferences(db_session, [first, second])
    await db_session.commit()

    db_session.flush = real_flush  # type: ignore[method-assign]

    rows = (
        await db_session.execute(
            select(NotificationPreferenceDB.user_id).order_by(
                NotificationPreferenceDB.user_id
            )
        )
    ).scalars().all()
    # The ids are compared as plain strings: the rollback inside the seed
    # expires the ORM objects, and reading an expired attribute of an
    # async session raises MissingGreenlet.
    assert list(rows) == ["user-seed-002"]


async def test_saved_searches_are_created_once(db_session):
    """The saved searches are looked up by user and name - that must hold."""
    user = await _make_user(db_session)

    await _seed_saved_searches(db_session, [user])
    await db_session.commit()
    await _seed_saved_searches(db_session, [user])
    await db_session.commit()

    count = await db_session.scalar(
        select(func.count())
        .select_from(SavedSearchDB)
        .where(SavedSearchDB.user_id == user.id)
    )
    assert count == 1


async def test_users_are_created_once(db_session):
    """The users are upserted by their id - a second pass changes nothing."""
    ids = await _seed_users(db_session)
    await db_session.commit()
    assert ids

    again = await _seed_users(db_session)
    await db_session.commit()
    assert again == ids

    count = await db_session.scalar(select(func.count()).select_from(User))
    assert count == len(ids)
