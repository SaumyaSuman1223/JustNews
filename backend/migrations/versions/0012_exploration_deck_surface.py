"""exploration deck: a fourth surface value, and its kill switch

Revision ID: 0012_exploration_deck_surface
Revises: 0011_feature_flags
Create Date: 2026-09-04

Stage 7's exploration deck needs a `surface` value of its own: the deck
replaces the onboarding topic-picker (which never logged an impression at
all - it was plain checkboxes) and is also mixed, at ~10%, into ordinary
`/v1/feed` pages. Both cases are "content shown because the ranker sampled
it stratified-by-topic rather than ranked it" - one surface value,
`'onboarding'`, covers both. A reader never knows a feed card came from the
exploratory slice rather than the ranked majority; the two are told apart
by `ranking_policy` (already an open column, no migration needed there),
not by `surface`.

`surface` keeps its CHECK - 0007's reasoning for narrowing `ranking_policy`
instead doesn't apply here: `surface` is still a genuinely closed, rarely-
growing set of product surfaces. `'onboarding'` is the fourth in the
lifetime of this schema.

Also seeds `exploration_deck`, following 0011's own precedent exactly: a
kill switch services.exploration_deck and the feed-wide 10% mix in
services.feed both check before doing anything that needs to be
switchable off without a deploy. Seeded `true` - turning it on is what
shipping this migration means.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0012_exploration_deck_surface"
down_revision: str | None = "0011_feature_flags"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_IMPRESSIONS_CONSTRAINT = "ck_impressions_surface"
_EVENTS_CONSTRAINT = "ck_interaction_events_surface"
_OLD = "'feed', 'explore', 'search', 'topic'"
_NEW = "'feed', 'explore', 'search', 'topic', 'onboarding'"


def upgrade() -> None:
    op.drop_constraint(_IMPRESSIONS_CONSTRAINT, "impressions", type_="check")
    op.create_check_constraint(_IMPRESSIONS_CONSTRAINT, "impressions", f"surface in ({_NEW})")
    op.drop_constraint(_EVENTS_CONSTRAINT, "interaction_events", type_="check")
    op.create_check_constraint(_EVENTS_CONSTRAINT, "interaction_events", f"surface in ({_NEW})")

    op.execute(
        """
        INSERT INTO feature_flags (key, enabled, description)
        VALUES (
            'exploration_deck',
            true,
            'Serve the Stage 7 stratified exploration deck (onboarding) and mix its ~10% slice into /v1/feed. Off falls back to the plain feed with no exploratory slots.'
        )
        """
    )


def downgrade() -> None:
    op.execute("delete from feature_flags where key = 'exploration_deck'")
    # A CHECK can't be narrowed while a row would violate it - anything
    # logged as 'onboarding' folds back into 'explore' (the closest existing
    # meaning: content shown without personalization) before the constraint
    # tightens again.
    op.execute("update impressions set surface = 'explore' where surface = 'onboarding'")
    op.execute("update interaction_events set surface = 'explore' where surface = 'onboarding'")
    op.drop_constraint(_EVENTS_CONSTRAINT, "interaction_events", type_="check")
    op.create_check_constraint(_EVENTS_CONSTRAINT, "interaction_events", f"surface in ({_OLD})")
    op.drop_constraint(_IMPRESSIONS_CONSTRAINT, "impressions", type_="check")
    op.create_check_constraint(_IMPRESSIONS_CONSTRAINT, "impressions", f"surface in ({_OLD})")
