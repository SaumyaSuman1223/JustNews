"""allow gnews_category as a topic provenance

Revision ID: 0006_gnews_topic_provenance
Revises: 0005_ranking_policy
Create Date: 2026-09-02

GNews backfill requests a specific category and attributes the resulting
articles to the matching IPTC concept. That is real evidence about the
subject - the same strength as a feed's own section - but it is not the same
evidence, so it gets its own name rather than being filed under `feed_hint`.

Alembic's autogenerate does not diff CHECK constraints, so this is written by
hand; the constraint is dropped and recreated because Postgres has no
ALTER CONSTRAINT for a check expression.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0006_gnews_topic_provenance"
down_revision: str | None = "0005_ranking_policy"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CONSTRAINT = "ck_article_topics_assigned_by"
_OLD = "assigned_by in ('mapping', 'classifier', 'feed_hint', 'manual')"
_NEW = "assigned_by in ('mapping', 'classifier', 'feed_hint', 'gnews_category', 'manual')"


def upgrade() -> None:
    op.drop_constraint(_CONSTRAINT, "article_topics", type_="check")
    op.create_check_constraint(_CONSTRAINT, "article_topics", _NEW)


def downgrade() -> None:
    # Rows written under the new vocabulary would violate the old constraint,
    # so they are relabelled to the closest thing it allows rather than left to
    # fail the migration. `feed_hint` is that: same confidence, same shape.
    op.execute(
        "update article_topics set assigned_by = 'feed_hint' where assigned_by = 'gnews_category'"
    )
    op.drop_constraint(_CONSTRAINT, "article_topics", type_="check")
    op.create_check_constraint(_CONSTRAINT, "article_topics", _OLD)
