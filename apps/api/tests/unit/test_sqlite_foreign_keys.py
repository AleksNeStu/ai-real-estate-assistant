"""SQLite enforces the foreign keys the schema declares.

SQLite does not enforce them by default, and the difference is not academic:
without the pragma an ON DELETE CASCADE never runs, so a child row outlives
the parent it points at. The demo's re-seed deletes every user on startup,
and the oauth_accounts links survived them - which left a sign-in that could
never finish, for every account, forever.

These tests run against the same pragma the deployments run with, and they
also hold the rule in place: an engine built anywhere in the application
goes through the factory, so a new one cannot quietly come unenforced.
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


@pytest.mark.asyncio
async def test_the_factory_gives_every_engine_the_pragma():
    """An engine built by the factory enforces the schema's rules.

    This is the property the rest of the application relies on: the demo's
    sign-in broke because one connection was made without the pragma.
    """
    from db.database import create_engine

    engine = create_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("PRAGMA foreign_keys"))
            assert result.scalar() == 1
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_a_second_connection_from_the_factory_also_enforces():
    """The pragma is per connection, so every new one has to be told.

    A pragma set on one connection does not carry to the next one - which
    is why the rule is applied by a listener rather than once at startup.
    """
    from db.database import create_engine

    engine = create_engine("sqlite+aiosqlite:///:memory:")
    try:
        for _ in range(3):
            async with engine.connect() as conn:
                result = await conn.execute(text("PRAGMA foreign_keys"))
                assert result.scalar() == 1
    finally:
        await engine.dispose()


def test_a_non_sqlite_engine_is_left_alone():
    """The pragma is SQLite's; Postgres enforces foreign keys already.

    A gate that fires on the wrong database is a gate that breaks a working
    deployment, so the helper asks the engine what it is.
    """
    from unittest.mock import MagicMock

    from db.database import enable_sqlite_foreign_keys

    engine = MagicMock()
    engine.url.get_backend_name.return_value = "postgresql"
    enable_sqlite_foreign_keys(engine)
    engine.sync_engine.listen.assert_not_called()


def test_every_engine_in_the_application_goes_through_the_factory():
    """No engine may be built without the pragma.

    The rule is only as good as the number of places that could break it, so
    this holds the count: an engine created outside the factory is a
    connection that does not enforce the schema's foreign keys, and the bug
    it causes is invisible until a child row outlives its parent.
    """
    import re
    from pathlib import Path

    api_root = Path(__file__).resolve().parents[2]
    # The factory itself. The migration engine is exempt too, and must stay
    # so: a table rebuild under enforced foreign keys deletes the child rows.
    allowed = {
        "db/database.py",
        "alembic/env.py",
        # The metrics database is a separate file with no relations; it goes
        # through its own helper, which sets the pragma the same way.
        "agents/classification_metrics.py",
    }
    # Vendored trees are not the application's code.
    skipped_dirs = {".venv", ".venv312", "venv", "node_modules", "__pycache__"}

    offenders = []
    for path in sorted(api_root.rglob("*.py")):
        relative = path.relative_to(api_root).as_posix()
        if relative in allowed:
            continue
        if "tests/" in f"{relative}/":
            continue
        if skipped_dirs & set(path.relative_to(api_root).parts):
            continue
        source = path.read_text(encoding="utf-8")
        if re.search(r"\bcreate_async_engine\s*\(", source) or re.search(
            r"\bsqlite3\.connect\s*\(", source
        ):
            offenders.append(relative)

    assert offenders == [], (
        "these build an engine without the pragma; build it with "
        "db.database.create_engine instead: " + ", ".join(offenders)
    )
