"""market snapshots and trending companies, for Discover's rail

Revision ID: 0019_market_widgets
Revises: 0018_story_follows
Create Date: 2026-09-23

Discover's Market Outlook and Trending Companies (docs/DISCOVER_PLAN.md).
Both are written only by the scheduled `justnews-ingest markets` job and
served from these tables, so no market API is ever called in a request path
and a free-tier quota cannot be spent by traffic.

Public data, read by every visitor, so RLS is on with a read-everything
policy and no write policy at all: Supabase exposes the public schema over
PostgREST, and without this an anonymous key could write a price. The job
connects as the table owner, which RLS does not apply to unless forced - it
is not forced here, on purpose.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0019_market_widgets"
down_revision: str | None = "0018_story_follows"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "market_snapshots",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(16), nullable=False),
        sa.Column("label", sa.String(60), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("change", sa.Float(), nullable=False),
        sa.Column("change_pct", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_market_snapshots_symbol_as_of", "market_snapshots", ["symbol", "as_of"])

    op.create_table(
        "company_mentions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("ticker", sa.String(16), nullable=False),
        sa.Column("exchange", sa.String(16), nullable=False),
        sa.Column("domain", sa.String(80), nullable=False),
        sa.Column("mentions", sa.Integer(), nullable=False),
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("change_pct", sa.Float(), nullable=True),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    for table in ("market_snapshots", "company_mentions"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"CREATE POLICY {table}_read ON {table} FOR SELECT USING (true)")


def downgrade() -> None:
    for table in ("company_mentions", "market_snapshots"):
        op.execute(f"DROP POLICY IF EXISTS {table}_read ON {table}")
    op.drop_table("company_mentions")
    op.drop_index("ix_market_snapshots_symbol_as_of", table_name="market_snapshots")
    op.drop_table("market_snapshots")
