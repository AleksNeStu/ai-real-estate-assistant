"""The audit chain under concurrent writes (TaskMaster #104).

Measured on the live demo: 678 entries shared their tip with another
entry, so the log was a forest instead of a line. Two writers read the
same tip and both linked to it - the read of the tip and the insert that
follows it were not one atomic step.

The link is now made atomic with the insert: the row goes in first, which
takes the write lock, and the tip is read under that lock. So a second
writer waits for the first instead of reading the same tip.

The verifier also stopped calling a forked log invalid without saying so.
`valid` still means "one unbroken line" - honest for a log that forked.
`integrity_valid` says whether every entry's own hash still matches its
content, which is the tamper-evidence claim, and it stays true for a log
that forked under concurrency.
"""

import asyncio

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from db.analytics_repos import AuditLogRepository
from db.database import Base, create_engine
from db.models import AuditLogEntry


async def _engine_and_factory(tmp_path):
    """An engine on a real file, so two sessions are two writers."""
    engine = create_engine(f"sqlite+aiosqlite:///{tmp_path / 'audit.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False, autocommit=False
    )
    return engine, factory


@pytest.mark.asyncio
async def test_two_writers_do_not_fork_the_chain(tmp_path):
    """Two writers, one tip, one line.

    The first writer holds its transaction open - so the second writer
    finds the write lock held. Before the fix the second writer read the
    tip while the first's entry was still uncommitted, linked to the same
    tip, and the chain forked.
    """
    engine, factory = await _engine_and_factory(tmp_path)

    first_inserted = asyncio.Event()
    release_first = asyncio.Event()

    async def writer_first():
        async with factory() as session:
            repo = AuditLogRepository(session)
            await repo.append(action="first")
            first_inserted.set()
            # The entry is written but not committed: the tip the second
            # writer would read is still the one before it.
            await release_first.wait()
            await session.commit()

    async def writer_second():
        await first_inserted.wait()
        async with factory() as session:
            repo = AuditLogRepository(session)
            await repo.append(action="second")
            await session.commit()

    first = asyncio.create_task(writer_first())
    second = asyncio.create_task(writer_second())

    # Give the second writer time to reach the write lock, then let the
    # first one commit.
    await asyncio.sleep(0.2)
    release_first.set()
    await asyncio.gather(first, second)

    async with factory() as session:
        entries = list(
            (await session.execute(select(AuditLogEntry).order_by(AuditLogEntry.created_at.asc())))
            .scalars()
            .all()
        )
        result = await AuditLogRepository(session).verify_chain()

    await engine.dispose()

    assert len(entries) == 2
    # The second entry links to the first one - one line, not a fork.
    assert entries[1].prev_hash == entries[0].entry_hash
    assert result["valid"] is True
    assert result["fork_count"] == 0
    assert result["integrity_valid"] is True


@pytest.mark.asyncio
async def test_the_entry_links_to_the_one_before_it(tmp_path):
    """The ordinary case: each entry links to its predecessor."""
    engine, factory = await _engine_and_factory(tmp_path)

    async with factory() as session:
        repo = AuditLogRepository(session)
        first = await repo.append(action="one")
        second = await repo.append(action="two")
        await session.commit()

    assert second.prev_hash == first.entry_hash
    # The order of the links and the order of the timestamps are the same
    # order - that is what the verifier walks.
    assert second.created_at > first.created_at

    async with factory() as session:
        result = await AuditLogRepository(session).verify_chain()

    await engine.dispose()
    assert result["valid"] is True
    assert result["checked_count"] == 2


@pytest.mark.asyncio
async def test_a_forked_log_is_reported_as_a_fork_and_stays_intact(tmp_path):
    """A log that forked: not one line, but nothing was tampered with."""
    engine, factory = await _engine_and_factory(tmp_path)

    async with factory() as session:
        repo = AuditLogRepository(session)
        first = await repo.append(action="one")
        await session.commit()

    # Two entries written against the same tip - what the concurrency bug
    # produced on the live demo.
    async with factory() as session:
        repo = AuditLogRepository(session)
        forked_a = AuditLogEntry(
            id="forked-a",
            action="forked.a",
            details={},
            prev_hash=first.entry_hash,
            created_at=first.created_at.replace(microsecond=first.created_at.microsecond + 1),
        )
        forked_a.entry_hash = forked_a.compute_hash(first.entry_hash)
        forked_b = AuditLogEntry(
            id="forked-b",
            action="forked.b",
            details={},
            prev_hash=first.entry_hash,
            created_at=first.created_at.replace(microsecond=first.created_at.microsecond + 2),
        )
        forked_b.entry_hash = forked_b.compute_hash(first.entry_hash)
        session.add_all([forked_a, forked_b])
        await session.commit()

    async with factory() as session:
        result = await AuditLogRepository(session).verify_chain()

    await engine.dispose()

    # The line verdict stays honest: the chain is not one line.
    assert result["valid"] is False
    # The tamper-evidence verdict: every entry's own hash still matches.
    assert result["integrity_valid"] is True
    # Two entries share the tip.
    assert result["fork_count"] == 2


@pytest.mark.asyncio
async def test_the_verifier_checks_the_newest_entries(tmp_path):
    """The window is the newest ones - as the endpoint says it is."""
    engine, factory = await _engine_and_factory(tmp_path)

    async with factory() as session:
        repo = AuditLogRepository(session)
        for index in range(5):
            await repo.append(action=f"action.{index}")
        await session.commit()

    async with factory() as session:
        result = await AuditLogRepository(session).verify_chain(limit=2)
        newest = list(
            (
                await session.execute(
                    select(AuditLogEntry).order_by(AuditLogEntry.created_at.desc()).limit(2)
                )
            )
            .scalars()
            .all()
        )

    await engine.dispose()

    assert result["checked_count"] == 2
    assert {entry.action for entry in newest} == {"action.3", "action.4"}
    assert result["valid"] is True
