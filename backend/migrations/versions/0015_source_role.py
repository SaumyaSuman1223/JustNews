"""Perspectives: a source's editorial role (ADR 0013)

Revision ID: 0015_source_role
Revises: 0014_follow_positions
Create Date: 2026-09-05

A perspective is a fact about who published an article, not a guess about
its text (ADR 0013) - so it needs a fact to hang off, and this is it.
`source_role` is nullable and unassigned by default: an unroled source keeps
appearing in a story's coverage exactly as before, it just does not
contribute to a perspective group until an admin assigns it one. Nothing is
seeded here - there is no real source catalogue in this schema to assign
roles to yet, and inventing placeholder roles for it would be exactly the
kind of unverifiable assertion this ADR exists to rule out.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015_source_role"
down_revision: str | None = "0014_follow_positions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CONSTRAINT = "ck_sources_role"
_CHECK_SQL = (
    "source_role is null or source_role in "
    "('wire', 'industry', 'government', 'academic', 'investor', 'consumer', 'public')"
)


def upgrade() -> None:
    op.add_column("sources", sa.Column("source_role", sa.String(length=20), nullable=True))
    op.create_check_constraint(_CONSTRAINT, "sources", _CHECK_SQL)


def downgrade() -> None:
    op.drop_constraint(_CONSTRAINT, "sources", type_="check")
    op.drop_column("sources", "source_role")
