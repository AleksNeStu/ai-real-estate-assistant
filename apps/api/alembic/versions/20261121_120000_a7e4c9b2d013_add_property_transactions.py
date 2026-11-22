"""add_property_transactions

Revision ID: a7e4c9b2d013
Revises: c4d8f2a1b7e9
Create Date: 2026-11-21 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision: str = "a7e4c9b2d013"  # pragma: allowlist secret - alembic revision id, not a credential
down_revision: Union[str, None] = "c4d8f2a1b7e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""
    op.create_table(
        "property_transactions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("external_id", sa.String(length=64), nullable=False),
        sa.Column("transaction_id", sa.String(length=64), nullable=True),
        sa.Column("deed_reference", sa.String(length=64), nullable=True),
        sa.Column("teryt", sa.String(length=16), nullable=True),
        sa.Column("city", sa.String(length=64), nullable=False),
        sa.Column("city_norm", sa.String(length=64), nullable=False),
        sa.Column("district", sa.String(length=64), nullable=True),
        sa.Column("street", sa.String(length=128), nullable=False),
        sa.Column("street_norm", sa.String(length=128), nullable=False),
        sa.Column("number", sa.String(length=16), nullable=True),
        sa.Column("area_sqm", sa.Float(), nullable=False),
        sa.Column("rooms", sa.Integer(), nullable=True),
        sa.Column("floor", sa.Integer(), nullable=True),
        sa.Column("price_brutto", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("market_type", sa.String(length=32), nullable=True),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("source_url", sa.String(length=512), nullable=True),
        sa.Column("x_2180", sa.Float(), nullable=True),
        sa.Column("y_2180", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_property_transactions")),
        sa.UniqueConstraint("external_id", name=op.f("uq_property_transactions_external_id")),
    )
    op.create_index(
        op.f("ix_property_transactions_city_date"),
        "property_transactions",
        ["city_norm", "transaction_date"],
        unique=False,
    )
    op.create_index(
        op.f("ix_property_transactions_city"), "property_transactions", ["city"], unique=False
    )
    op.create_index(
        op.f("ix_property_transactions_city_norm"),
        "property_transactions",
        ["city_norm"],
        unique=False,
    )
    op.create_index(
        op.f("ix_property_transactions_external_id"),
        "property_transactions",
        ["external_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_property_transactions_market_type"),
        "property_transactions",
        ["market_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_property_transactions_source"), "property_transactions", ["source"], unique=False
    )
    op.create_index(
        op.f("ix_property_transactions_street"),
        "property_transactions",
        ["street"],
        unique=False,
    )
    op.create_index(
        op.f("ix_property_transactions_street_date"),
        "property_transactions",
        ["city_norm", "street_norm", "transaction_date"],
        unique=False,
    )
    op.create_index(
        op.f("ix_property_transactions_street_norm"),
        "property_transactions",
        ["street_norm"],
        unique=False,
    )
    op.create_index(
        op.f("ix_property_transactions_teryt"), "property_transactions", ["teryt"], unique=False
    )
    op.create_index(
        op.f("ix_property_transactions_transaction_date"),
        "property_transactions",
        ["transaction_date"],
        unique=False,
    )
    op.create_index(
        op.f("ix_property_transactions_transaction_id"),
        "property_transactions",
        ["transaction_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade database schema."""
    op.drop_index(
        op.f("ix_property_transactions_transaction_date"), table_name="property_transactions"
    )
    op.drop_index(
        op.f("ix_property_transactions_transaction_id"), table_name="property_transactions"
    )
    op.drop_index(op.f("ix_property_transactions_teryt"), table_name="property_transactions")
    op.drop_index(op.f("ix_property_transactions_street_norm"), table_name="property_transactions")
    op.drop_index(op.f("ix_property_transactions_street_date"), table_name="property_transactions")
    op.drop_index(op.f("ix_property_transactions_street"), table_name="property_transactions")
    op.drop_index(op.f("ix_property_transactions_source"), table_name="property_transactions")
    op.drop_index(op.f("ix_property_transactions_market_type"), table_name="property_transactions")
    op.drop_index(op.f("ix_property_transactions_external_id"), table_name="property_transactions")
    op.drop_index(op.f("ix_property_transactions_city_norm"), table_name="property_transactions")
    op.drop_index(op.f("ix_property_transactions_city"), table_name="property_transactions")
    op.drop_index(op.f("ix_property_transactions_city_date"), table_name="property_transactions")
    op.drop_table("property_transactions")
