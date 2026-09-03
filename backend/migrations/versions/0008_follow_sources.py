"""follow sources, not just topics

Revision ID: 0008_follow_sources
Revises: 0007_open_ranking_policy
Create Date: 2026-09-03

Google News calls this Preferred Sources. Follows have only ever covered
topics here; a reader who trusts one publisher over another had no way to say
so.

The RLS policy is a copy of user_follows' - deliberately, not by accident:
this is user-owned data with exactly the same ownership rules, and diverging
would be a bug rather than a design.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_follow_sources"
down_revision: str | None = "0007_open_ranking_policy"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Same expression the Stage 4 policies use: the session GUC the API sets per
# request (ADR 0007). Repeated rather than imported so this migration keeps
# working if that module is ever refactored.
CURRENT_USER_ID_EXPR = "nullif(current_setting('app.user_id', true), '')::uuid"


def upgrade() -> None:
    op.create_table(
        "user_source_follows",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "source_id", name="uq_user_source_follows_user_source"),
    )
    op.create_index("ix_user_source_follows_user", "user_source_follows", ["user_id"])

    op.execute("ALTER TABLE user_source_follows ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE user_source_follows FORCE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY user_source_follows_owner ON user_source_follows
        USING (user_id = {CURRENT_USER_ID_EXPR} OR is_current_user_admin())
        WITH CHECK (user_id = {CURRENT_USER_ID_EXPR})
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS user_source_follows_owner ON user_source_follows")
    op.drop_index("ix_user_source_follows_user", table_name="user_source_follows")
    op.drop_table("user_source_follows")
