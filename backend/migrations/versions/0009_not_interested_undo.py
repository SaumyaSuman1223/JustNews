"""a reversible "not interested" - undo without deleting the log

Revision ID: 0009_not_interested_undo
Revises: 0008_follow_sources
Create Date: 2026-09-03

`services.interactions`' own docstring calls `interaction_events` "an
append-only log ... which is what the Stage 6 ranker eventually trains on."
Physically deleting a `not_interested` row to implement undo would violate
that - Stage 6's offline evaluators would silently lose evidence that the
policy showed something and got a negative signal, which is a worse kind of
bias than the one propensity logging exists to prevent.

So undo is a new event, `not_interested_undo`, the same shape `save`/`unsave`
already use as a paired action - not a deletion. `excluded_article_ids`
(repositories.interactions) now reads the latest of the two per article
rather than "any not_interested row ever exists," so a reader who undoes and
later re-marks the same article is excluded again correctly.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0009_not_interested_undo"
down_revision: str | None = "0008_follow_sources"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CONSTRAINT = "ck_interaction_events_type"
_OLD_TYPES = "'click', 'save', 'unsave', 'share', 'not_interested', 'dwell'"
_NEW_TYPES = "'click', 'save', 'unsave', 'share', 'not_interested', 'not_interested_undo', 'dwell'"


def upgrade() -> None:
    op.drop_constraint(_CONSTRAINT, "interaction_events", type_="check")
    op.create_check_constraint(
        _CONSTRAINT, "interaction_events", f"event_type in ({_NEW_TYPES})"
    )


def downgrade() -> None:
    # A reader who undid a not_interested mark loses that specific reversal
    # on downgrade - the original not_interested row (which the old
    # constraint already allows) stands again, which is the same "excluded"
    # state the pre-undo product had. Lossy, same as 0007's downgrade, for
    # the same reason: the argument for the new constraint, not against
    # writing a clean downgrade.
    op.execute("delete from interaction_events where event_type = 'not_interested_undo'")
    op.drop_constraint(_CONSTRAINT, "interaction_events", type_="check")
    op.create_check_constraint(
        _CONSTRAINT, "interaction_events", f"event_type in ({_OLD_TYPES})"
    )
