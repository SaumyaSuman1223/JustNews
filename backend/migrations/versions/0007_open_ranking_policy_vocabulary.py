"""ranking_policy is an open vocabulary, not a closed one

Revision ID: 0007_open_ranking_policy
Revises: 0006_gnews_topic_provenance
Create Date: 2026-09-02

Stage 5 constrained `impressions.ranking_policy` to the two policies that
existed at the time. That made shipping a third ranker require a migration -
the exact coupling services.feed's policy registry exists to remove, and a
constraint the registry's own tests already enforce more usefully in code.

`surface` keeps its CHECK: it is a genuinely closed set of product surfaces.
`ranking_policy` is expected to grow with every experiment, so it does not.
The column is also widened, since real policy names ("finding_grouped_v1")
run past the original 20 characters.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_open_ranking_policy"
down_revision: str | None = "0006_gnews_topic_provenance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CONSTRAINT = "ck_impressions_ranking_policy"


def upgrade() -> None:
    op.drop_constraint(_CONSTRAINT, "impressions", type_="check")
    op.alter_column(
        "impressions",
        "ranking_policy",
        existing_type=sa.String(20),
        type_=sa.String(40),
        existing_nullable=False,
    )


def downgrade() -> None:
    # Anything served by a policy the old constraint never knew about is
    # relabelled rather than left to fail the migration. It is lossy, which is
    # itself the argument against the constraint.
    op.execute(
        "update impressions set ranking_policy = 'chronological' "
        "where ranking_policy not in ('chronological', 'heuristic_v1')"
    )
    op.alter_column(
        "impressions",
        "ranking_policy",
        existing_type=sa.String(40),
        type_=sa.String(20),
        existing_nullable=False,
    )
    op.create_check_constraint(
        _CONSTRAINT, "impressions", "ranking_policy in ('chronological', 'heuristic_v1')"
    )
