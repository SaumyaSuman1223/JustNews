"""feature flags

Revision ID: 0011_feature_flags
Revises: 0010_feedback
Create Date: 2026-09-04

The Stage 4 admin console checklist item, given its first real consumer
here rather than shipped as dead infrastructure: a kill switch for the
Stage 5 heuristic ranker (services/feed.py) - if it misbehaves for real
beta readers, an admin can force everyone to the chronological control
without a code deploy.

Read is open to any session, not admin-only like invite_codes and
admin_audit_log: services/feed.py checks the flag on an ordinary reader's
own request, running under that reader's own ``app.user_id``, not an
admin's. Only writes (creating or toggling a flag) are admin-gated.

Seeds one row, ``heuristic_ranker`` enabled - matching what is already
live today, so this migration changes nothing about who sees what the
moment it runs. A flag key with no row at all reads as enabled too
(``repositories.flags.is_enabled``'s default), so the seed row exists
for the admin UI to have something to show, not because the read path
depends on it.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011_feature_flags"
down_revision: str | None = "0010_feedback"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "feature_flags",
        sa.Column("key", sa.String(length=60), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("updated_by", sa.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["updated_by"], ["user_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("key"),
    )

    op.execute("ALTER TABLE feature_flags ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE feature_flags FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY feature_flags_read ON feature_flags
        FOR SELECT
        USING (true)
        """
    )
    op.execute(
        """
        CREATE POLICY feature_flags_insert ON feature_flags
        FOR INSERT
        WITH CHECK (is_current_user_admin())
        """
    )
    op.execute(
        """
        CREATE POLICY feature_flags_update ON feature_flags
        FOR UPDATE
        USING (is_current_user_admin())
        WITH CHECK (is_current_user_admin())
        """
    )
    op.execute(
        """
        CREATE POLICY feature_flags_delete ON feature_flags
        FOR DELETE
        USING (is_current_user_admin())
        """
    )

    op.execute(
        """
        INSERT INTO feature_flags (key, enabled, description)
        VALUES (
            'heuristic_ranker',
            true,
            'Serve the Stage 5 heuristic ranker to its A/B bucket. Off forces every reader to the chronological control.'
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS feature_flags_delete ON feature_flags")
    op.execute("DROP POLICY IF EXISTS feature_flags_update ON feature_flags")
    op.execute("DROP POLICY IF EXISTS feature_flags_insert ON feature_flags")
    op.execute("DROP POLICY IF EXISTS feature_flags_read ON feature_flags")
    op.drop_table("feature_flags")
