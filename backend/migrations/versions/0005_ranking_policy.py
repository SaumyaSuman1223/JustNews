"""ranking policy on impressions, for the stage 5 A/B harness

Revision ID: 0005_ranking_policy
Revises: 0004_admin_and_beta_gate
Create Date: 2026-09-03 00:00:00.000000+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_ranking_policy"
down_revision: str | None = "0004_admin_and_beta_gate"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # NOT NULL on a populated table needs a server default for existing rows;
    # every impression logged before this migration was chronological, since
    # no ranker existed yet.
    op.add_column(
        "impressions",
        sa.Column(
            "ranking_policy", sa.String(length=20), nullable=False, server_default="chronological"
        ),
    )
    op.alter_column("impressions", "ranking_policy", server_default=None)
    op.create_check_constraint(
        "ck_impressions_ranking_policy",
        "impressions",
        "ranking_policy in ('chronological', 'heuristic_v1')",
    )
    op.create_index(
        "ix_impressions_policy_served", "impressions", ["ranking_policy", sa.text("served_at DESC")]
    )


def downgrade() -> None:
    op.drop_index("ix_impressions_policy_served", table_name="impressions")
    op.drop_constraint("ck_impressions_ranking_policy", "impressions", type_="check")
    op.drop_column("impressions", "ranking_policy")
