"""follow a story, and remember when the reader last looked at it

Revision ID: 0018_story_follows
Revises: 0017_story_cluster_country_count
Create Date: 2026-09-23

Fifth pass F2. Topics and sources can be followed; a single developing
story could not, so a reader who cared how one event unfolded had no way to
come back to it except searching again. `last_seen_at` is when this reader
last opened the story page - what "3 new reports since you looked" counts
from. Deleted with the story cluster: a story that no longer exists is not
something anyone can still be following.

The RLS policy is a copy of user_follows' and user_source_follows' - same
ownership rules, and diverging would be a bug rather than a design.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018_story_follows"
down_revision: str | None = "0017_story_cluster_country_count"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Same expression the Stage 4 policies use: the session GUC the API sets per
# request (ADR 0007). Repeated rather than imported so this migration keeps
# working if that module is ever refactored.
CURRENT_USER_ID_EXPR = "nullif(current_setting('app.user_id', true), '')::uuid"


def upgrade() -> None:
    op.create_table(
        "user_story_follows",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("story_cluster_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["story_cluster_id"], ["story_clusters.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "story_cluster_id", name="uq_user_story_follows_user_story"),
    )
    op.create_index("ix_user_story_follows_user", "user_story_follows", ["user_id"])

    op.execute("ALTER TABLE user_story_follows ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE user_story_follows FORCE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY user_story_follows_owner ON user_story_follows
        USING (user_id = {CURRENT_USER_ID_EXPR} OR is_current_user_admin())
        WITH CHECK (user_id = {CURRENT_USER_ID_EXPR})
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS user_story_follows_owner ON user_story_follows")
    op.drop_index("ix_user_story_follows_user", table_name="user_story_follows")
    op.drop_table("user_story_follows")
