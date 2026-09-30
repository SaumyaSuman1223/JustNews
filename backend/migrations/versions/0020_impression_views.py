"""a 'top' surface, and which served impressions a reader actually saw

Revision ID: 0020_impression_views
Revises: 0019_market_widgets
Create Date: 2026-09-30

Two changes for the logging the recommender learns from (ADR 0015).

`surface` gains `'top'`, its seventh value: Discover's Top view is served by
the ranker from now on and logs impressions like For You does, and "the
importance order everyone gets" is a different surface from a personal feed.

`impression_views` records that a served card was on screen - at least half
visible for a second - and where it was drawn. An impression is written when
a page is served, which includes cards below the fold and the next page
Discover fetches ahead of the scroll; counting all of those as "shown and
not clicked" made most negatives wrong. A separate append-only table rather
than a column on `impressions`, which stays written once, at serve time, by
the policy that decided it: a view is reported later, by the client, the way
an interaction event is. One row per impression at most (the primary key),
so a card scrolled past twice is one view.

`rendered_position` is the card's place in the order it was drawn, which the
layout may move a few slots from the served order, and `slot` its shape -
position bias on a lead card is not position bias on a row.

RLS follows the impression: a view row is visible exactly when its
impression is, since the policy's EXISTS runs under the impressions table's
own policy.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0020_impression_views"
down_revision: str | None = "0019_market_widgets"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_IMPRESSIONS_CONSTRAINT = "ck_impressions_surface"
_EVENTS_CONSTRAINT = "ck_interaction_events_surface"
_OLD = "'feed', 'explore', 'search', 'topic', 'onboarding', 'aquila'"
_NEW = "'feed', 'explore', 'search', 'topic', 'onboarding', 'aquila', 'top'"


def upgrade() -> None:
    op.drop_constraint(_IMPRESSIONS_CONSTRAINT, "impressions", type_="check")
    op.create_check_constraint(_IMPRESSIONS_CONSTRAINT, "impressions", f"surface in ({_NEW})")
    op.drop_constraint(_EVENTS_CONSTRAINT, "interaction_events", type_="check")
    op.create_check_constraint(_EVENTS_CONSTRAINT, "interaction_events", f"surface in ({_NEW})")

    op.create_table(
        "impression_views",
        sa.Column(
            "impression_id",
            sa.BigInteger(),
            sa.ForeignKey("impressions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "viewed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("rendered_position", sa.SmallInteger(), nullable=False),
        sa.Column("slot", sa.String(8), nullable=False),
        sa.CheckConstraint("rendered_position >= 0", name="ck_impression_views_position"),
        sa.CheckConstraint(
            "slot in ('lead', 'wide', 'card', 'row', 'page')", name="ck_impression_views_slot"
        ),
    )
    op.execute("ALTER TABLE impression_views ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE impression_views FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY impression_views_follow_impression ON impression_views
        USING (EXISTS (SELECT 1 FROM impressions i WHERE i.id = impression_id))
        WITH CHECK (EXISTS (SELECT 1 FROM impressions i WHERE i.id = impression_id))
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY impression_views_follow_impression ON impression_views")
    op.drop_table("impression_views")
    # A CHECK can't be narrowed while a row would violate it - 'top' folds
    # back into 'feed', the surface Top was served beside before it had one.
    op.execute("update impressions set surface = 'feed' where surface = 'top'")
    op.execute("update interaction_events set surface = 'feed' where surface = 'top'")
    op.drop_constraint(_EVENTS_CONSTRAINT, "interaction_events", type_="check")
    op.create_check_constraint(_EVENTS_CONSTRAINT, "interaction_events", f"surface in ({_OLD})")
    op.drop_constraint(_IMPRESSIONS_CONSTRAINT, "impressions", type_="check")
    op.create_check_constraint(_IMPRESSIONS_CONSTRAINT, "impressions", f"surface in ({_OLD})")
