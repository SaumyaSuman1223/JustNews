"""Story clusters: country_count

Revision ID: 0017_story_cluster_country_count
Revises: 0016_issue_focus_role
Create Date: 2026-09-08

Third-pass audit §21: "7 sources / 4 countries / 3 perspectives / 2
languages" on a significant, multi-source story. `source_count` and
`language_count` already exist and are maintained by
`dedup.refresh_cluster_counts`; country does not live on `Article` at all -
it is a property of the publisher (`Source.country`) - so counting it means
a join `refresh_cluster_counts` did not previously need to make.

Nullable-free, defaulted to 0: every existing cluster is correct at 0 until
`justnews-ingest repair-cluster-counts` (added alongside this migration)
recomputes it from the real data, the same additive-then-backfill shape
`0015_source_role` and the entity/furniture text cleanup used. A `NOT NULL`
column with a server default needs no data migration of its own - Postgres
fills existing rows at the default without a table rewrite lock on modern
versions, which is why this is a plain `add_column` rather than a two-step
nullable-then-backfill-then-not-null dance.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017_story_cluster_country_count"
down_revision: str | None = "0016_issue_focus_role"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "story_clusters",
        sa.Column("country_count", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("story_clusters", "country_count")
