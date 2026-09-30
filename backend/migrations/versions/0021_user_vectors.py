"""user vectors from the FINDING user tower, and the jobs that read logs

Revision ID: 0021_user_vectors
Revises: 0020_impression_views
Create Date: 2026-09-30

`user_vectors` holds one vector per reader from the FINDING user tower
(ADR 0016): computed offline by `justnews-ingest user-vectors` from the
exported ONNX model, read by the `finding_v1` ranking policy as the
reader's profile - a dot product with stored article vectors, no inference
in the request path (ADR 0004). `group_id` is the reader's FINDING group,
`model_version` the model that wrote it.

Two offline jobs read across readers: `user-vectors` (every reader's
opens, shares and saves, to write every reader's vector) and
`export-behaviours` (consented impressions, views and clicks, for the
offline replay that compares rankers - ADR 0016). Everything here connects
as the tables' owner with RLS forced, so neither can do that as one reader
(`app.user_id`). Each says what it is instead - `app.job`, set per
transaction by `justnews_core.db.set_job` - and these policies let exactly
those jobs read the tables they need, and only `user-vectors` write
vectors. They are added beside the owner policies, not in place of them:
permissive policies are ORed, so every existing check stays as it was.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from justnews_core.models import EMBEDDING_DIM, EmbeddingVector

revision: str = "0021_user_vectors"
down_revision: str | None = "0020_impression_views"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CURRENT_USER_ID = "NULLIF(current_setting('app.user_id', true), '')::uuid"
JOB = "current_setting('app.job', true) = 'user-vectors'"
READER_JOBS = "current_setting('app.job', true) IN ('user-vectors', 'export-behaviours')"
_JOB_READS = (
    "user_profiles",
    "interaction_events",
    "user_saves",
    "impressions",
    "impression_views",
)


def upgrade() -> None:
    op.create_table(
        "user_vectors",
        sa.Column(
            "user_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("user_profiles.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("model_version", sa.String(40), nullable=False),
        sa.Column("group_id", sa.SmallInteger(), nullable=True),
        sa.Column("vector", EmbeddingVector(EMBEDDING_DIM), nullable=False),
        sa.Column("history_count", sa.Integer(), nullable=False),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.execute("ALTER TABLE user_vectors ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE user_vectors FORCE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY user_vectors_owner ON user_vectors
        USING (user_id = {CURRENT_USER_ID} OR is_current_user_admin())
        """
    )
    op.execute(
        f"""
        CREATE POLICY user_vectors_job ON user_vectors
        USING ({JOB}) WITH CHECK ({JOB})
        """
    )
    for table in _JOB_READS:
        op.execute(f"CREATE POLICY {table}_ranker_jobs ON {table} FOR SELECT USING ({READER_JOBS})")


def downgrade() -> None:
    for table in _JOB_READS:
        op.execute(f"DROP POLICY {table}_ranker_jobs ON {table}")
    op.execute("DROP POLICY user_vectors_job ON user_vectors")
    op.execute("DROP POLICY user_vectors_owner ON user_vectors")
    op.drop_table("user_vectors")
