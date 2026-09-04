"""The Aquila Tribune: published issues, and a sixth surface

Revision ID: 0013_aquila_issues
Revises: 0012_exploration_deck_surface
Create Date: 2026-09-04

Aquila is a publication, not a feed (ADR 0012). An issue is composed once,
offline, at its publish time and never changes afterwards, so serving it is a
keyed read of frozen rows rather than the most expensive query in the product
running on its hottest path. Three tables carry that: `issues` (which
edition, which day, its masthead numbering), `issue_pages` (the running
order, and which IPTC concept each section page was drawn from) and
`issue_slots` (which article sits in which position, at which composition
weight).

`issues` is deliberately not `editions`. That table already exists and means
a *regional* edition - a language/country pairing - so Aquila's
morning/midday/evening is an `edition_slot` column here. Reusing the word
would have put two unrelated concepts behind one name in the same schema.

`surface` also gains `'aquila'`, its sixth value in the lifetime of this
schema. A composed page is still a selection the system made on the reader's
behalf, so it logs impressions like every other surface - Stage 6 has to be
able to replay what Aquila showed, and an impression that was never written
cannot be backfilled.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013_aquila_issues"
down_revision: str | None = "0012_exploration_deck_surface"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_IMPRESSIONS_CONSTRAINT = "ck_impressions_surface"
_EVENTS_CONSTRAINT = "ck_interaction_events_surface"
_OLD = "'feed', 'explore', 'search', 'topic', 'onboarding'"
_NEW = "'feed', 'explore', 'search', 'topic', 'onboarding', 'aquila'"


def upgrade() -> None:
    op.create_table(
        "issues",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("locale", sa.String(length=12), nullable=False),
        sa.Column("edition_slot", sa.String(length=8), nullable=False),
        sa.Column("published_on", sa.Date(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("volume", sa.Integer(), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        # One issue per locale per slot per day. This is what makes the
        # composer safe to re-run: a second attempt at the same edition
        # conflicts rather than quietly publishing a duplicate.
        sa.UniqueConstraint("locale", "published_on", "edition_slot", name="uq_issues_slot"),
        sa.CheckConstraint(
            "edition_slot in ('morning', 'midday', 'evening')", name="ck_issues_edition_slot"
        ),
    )
    op.create_index(
        "ix_issues_locale_published", "issues", ["locale", sa.text("published_at DESC")]
    )

    op.create_table(
        "issue_pages",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("issue_id", sa.BigInteger(), nullable=False),
        sa.Column("page_no", sa.SmallInteger(), nullable=False),
        sa.Column("topic_id", sa.String(length=32), nullable=True),
        sa.ForeignKeyConstraint(["issue_id"], ["issues.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("issue_id", "page_no", name="uq_issue_pages_page_no"),
    )
    op.create_index("ix_issue_pages_issue_id", "issue_pages", ["issue_id"])

    op.create_table(
        "issue_slots",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("page_id", sa.BigInteger(), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("article_id", sa.BigInteger(), nullable=False),
        sa.Column("role", sa.String(length=12), nullable=False),
        sa.ForeignKeyConstraint(["page_id"], ["issue_pages.id"], ondelete="CASCADE"),
        # CASCADE, not SET NULL: retention prunes articles at ninety days and
        # a slot without its article has nothing to render.
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("page_id", "position", name="uq_issue_slots_position"),
        sa.CheckConstraint("role in ('lead', 'secondary', 'brief')", name="ck_issue_slots_role"),
    )
    op.create_index("ix_issue_slots_page_id", "issue_slots", ["page_id"])
    op.create_index("ix_issue_slots_article_id", "issue_slots", ["article_id"])

    op.drop_constraint(_IMPRESSIONS_CONSTRAINT, "impressions", type_="check")
    op.create_check_constraint(_IMPRESSIONS_CONSTRAINT, "impressions", f"surface in ({_NEW})")
    op.drop_constraint(_EVENTS_CONSTRAINT, "interaction_events", type_="check")
    op.create_check_constraint(_EVENTS_CONSTRAINT, "interaction_events", f"surface in ({_NEW})")

    op.execute(
        """
        INSERT INTO feature_flags (key, enabled, description)
        VALUES (
            'aquila',
            true,
            'Serve The Aquila Tribune. Off returns no issue, and the Aquila route renders its "no issue yet" state rather than erroring.'
        )
        """
    )


def downgrade() -> None:
    op.execute("delete from feature_flags where key = 'aquila'")
    # A CHECK cannot be narrowed while a row would violate it. Aquila
    # impressions fold into 'explore' - the closest existing meaning, content
    # shown without personalisation.
    op.execute("update impressions set surface = 'explore' where surface = 'aquila'")
    op.execute("update interaction_events set surface = 'explore' where surface = 'aquila'")
    op.drop_constraint(_EVENTS_CONSTRAINT, "interaction_events", type_="check")
    op.create_check_constraint(_EVENTS_CONSTRAINT, "interaction_events", f"surface in ({_OLD})")
    op.drop_constraint(_IMPRESSIONS_CONSTRAINT, "impressions", type_="check")
    op.create_check_constraint(_IMPRESSIONS_CONSTRAINT, "impressions", f"surface in ({_OLD})")

    op.drop_table("issue_slots")
    op.drop_table("issue_pages")
    op.drop_table("issues")
