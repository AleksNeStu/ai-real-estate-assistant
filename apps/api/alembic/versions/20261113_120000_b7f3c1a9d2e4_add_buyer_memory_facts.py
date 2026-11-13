"""add_buyer_memory_facts

Revision ID: b7f3c1a9d2e4
Revises: 103eadae4a99
Create Date: 2026-11-13 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision: str = "b7f3c1a9d2e4"  # pragma: allowlist secret - alembic revision id, not a credential
down_revision: Union[str, None] = "103eadae4a99"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""
    op.create_table(
        "buyer_memory_facts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("listing_id", sa.String(length=36), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_buyer_memory_facts_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_buyer_memory_facts")),
    )
    op.create_index(
        op.f("ix_buyer_memory_facts_user_id"), "buyer_memory_facts", ["user_id"], unique=False
    )


def downgrade() -> None:
    """Downgrade database schema."""
    op.drop_index(op.f("ix_buyer_memory_facts_user_id"), table_name="buyer_memory_facts")
    op.drop_table("buyer_memory_facts")
