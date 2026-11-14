"""deal_and_commission_agent_link_may_be_null

Revision ID: c4d8f2a1b7e9
Revises: b7f3c1a9d2e4
Create Date: 2026-11-14 11:00:00.000000

The two columns carried "ON DELETE SET NULL" on a NOT NULL column. The rule
could never be carried out: with foreign keys enforced, deleting the agent's
account was refused with "NOT NULL constraint failed" instead of dropping the
link. The columns are widened so the rule they declare can actually happen.

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision: str = "c4d8f2a1b7e9"  # pragma: allowlist secret - alembic revision id, not a credential
down_revision: Union[str, None] = "b7f3c1a9d2e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""
    # SQLite cannot drop a NOT NULL constraint in place - the column has to be
    # rebuilt - and Alembic's batch mode does that for us.
    with op.batch_alter_table("deals") as batch_op:
        batch_op.alter_column(
            "agent_id",
            existing_type=sa.String(length=36),
            nullable=True,
        )
    with op.batch_alter_table("commissions") as batch_op:
        batch_op.alter_column(
            "agent_id",
            existing_type=sa.String(length=36),
            nullable=True,
        )


def downgrade() -> None:
    """Downgrade database schema."""
    with op.batch_alter_table("commissions") as batch_op:
        batch_op.alter_column(
            "agent_id",
            existing_type=sa.String(length=36),
            nullable=False,
        )
    with op.batch_alter_table("deals") as batch_op:
        batch_op.alter_column(
            "agent_id",
            existing_type=sa.String(length=36),
            nullable=False,
        )
