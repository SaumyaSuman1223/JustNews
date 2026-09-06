"""Aquila: the IN FOCUS slot role

Revision ID: 0016_issue_focus_role
Revises: 0015_source_role
Create Date: 2026-09-06

The front page's left rail runs one piece under a standing IN FOCUS label -
not the lead, not a column, not a line in the brief. That is a fourth
composition weight, so it is a fourth value in the role vocabulary.

Widening a CHECK is additive: every row written under the old vocabulary is
still valid under the new one, so this needs no data migration and no
rewrite. The downgrade is the one direction that can fail, because a `focus`
row written since the upgrade would violate the narrower constraint - so it
demotes those rows to 'secondary' first. A demoted slot still renders; it
just renders as a column rather than in the rail, which is the correct
behaviour for a database that has been told the role no longer exists.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0016_issue_focus_role"
down_revision: str | None = "0015_source_role"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CONSTRAINT = "ck_issue_slots_role"
_NEW_SQL = "role in ('lead', 'focus', 'secondary', 'brief')"
_OLD_SQL = "role in ('lead', 'secondary', 'brief')"


def upgrade() -> None:
    op.drop_constraint(_CONSTRAINT, "issue_slots", type_="check")
    op.create_check_constraint(_CONSTRAINT, "issue_slots", _NEW_SQL)


def downgrade() -> None:
    op.drop_constraint(_CONSTRAINT, "issue_slots", type_="check")
    op.execute("update issue_slots set role = 'secondary' where role = 'focus'")
    op.create_check_constraint(_CONSTRAINT, "issue_slots", _OLD_SQL)
