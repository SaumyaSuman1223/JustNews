"""a feedback table

Revision ID: 0010_feedback
Revises: 0009_not_interested_undo
Create Date: 2026-09-04

Free text a reader sends in from the footer link or account menu. No email
column, per CLAUDE.md's "log user IDs, never emails" - ``user_id`` is the
identifier, and it anonymizes the same way an interaction row does on
account deletion.

Not RLS'd like ``user_source_follows``: there is deliberately no "list my
own feedback" endpoint (nothing reads it back except the admin console),
so the owner-or-admin read policy those tables use is not what this needs.
Insert-only-by-owner, admin-readable, is the whole shape.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_feedback"
down_revision: str | None = "0009_not_interested_undo"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Same expression the Stage 4 policies use: the session GUC the API sets per
# request (ADR 0007). Repeated rather than imported so this migration keeps
# working if that module is ever refactored.
CURRENT_USER_ID_EXPR = "nullif(current_setting('app.user_id', true), '')::uuid"


def upgrade() -> None:
    op.create_table(
        "feedback",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("session_id", sa.String(length=64), nullable=True),
        sa.Column("locale", sa.String(length=12), nullable=False),
        sa.Column("path", sa.Text(), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_feedback_created", "feedback", [sa.text("created_at DESC")])

    op.execute("ALTER TABLE feedback ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE feedback FORCE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY feedback_insert_own ON feedback
        FOR INSERT
        WITH CHECK (user_id = {CURRENT_USER_ID_EXPR})
        """
    )
    op.execute(
        """
        CREATE POLICY feedback_admin_read ON feedback
        FOR SELECT
        USING (is_current_user_admin())
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS feedback_admin_read ON feedback")
    op.execute("DROP POLICY IF EXISTS feedback_insert_own ON feedback")
    op.drop_index("ix_feedback_created", table_name="feedback")
    op.drop_table("feedback")
