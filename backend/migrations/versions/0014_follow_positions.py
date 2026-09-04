"""My Desk: a reader-chosen order for followed topics

Revision ID: 0014_follow_positions
Revises: 0013_aquila_issues
Create Date: 2026-09-04

`user_follows` had no ordering column - the API always returned it sorted by
`created_at`, which is fine until a reader wants to put their most-read topic
first. `position` is a plain integer per user, backfilled from the existing
`created_at` order so no reader's current arrangement changes on deploy.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014_follow_positions"
down_revision: str | None = "0013_aquila_issues"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_follows",
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
    )
    # Backfill: each reader's existing follows keep their created_at order.
    op.execute(
        """
        UPDATE user_follows AS uf
        SET position = ranked.rn
        FROM (
            SELECT id, ROW_NUMBER() OVER (
                PARTITION BY user_id ORDER BY created_at, id
            ) - 1 AS rn
            FROM user_follows
        ) AS ranked
        WHERE uf.id = ranked.id
        """
    )
    op.alter_column("user_follows", "position", server_default=None)


def downgrade() -> None:
    op.drop_column("user_follows", "position")
