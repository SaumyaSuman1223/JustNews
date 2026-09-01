"""admin role, moderation, invite codes, and audit log

Revision ID: 0004_admin_and_beta_gate
Revises: 0003_users_and_interactions
Create Date: 2026-09-02 00:00:00.000000+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from justnews_core.models import CURRENT_USER_ID_EXPR

revision: str = "0004_admin_and_beta_gate"
down_revision: str | None = "0003_users_and_interactions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# RLS-protected tables whose owner-only policy needs widening so an admin can
# read every row, not just their own - the analytics and moderation queries
# the admin console runs are exactly that.
_ADMIN_READABLE_TABLES = ("user_saves", "user_follows", "impressions", "interaction_events")


def upgrade() -> None:
    op.add_column(
        "user_profiles",
        sa.Column("role", sa.String(length=20), nullable=False, server_default="reader"),
    )
    op.add_column("user_profiles", sa.Column("invite_redeemed_at", sa.DateTime(timezone=True)))
    op.add_column("user_profiles", sa.Column("redeemed_invite_code", sa.String(length=40)))
    op.alter_column("user_profiles", "role", server_default=None)
    op.create_check_constraint(
        "ck_user_profiles_role", "user_profiles", "role in ('reader', 'admin')"
    )

    op.add_column("articles", sa.Column("removed_at", sa.DateTime(timezone=True)))
    op.add_column("articles", sa.Column("removed_reason", sa.Text()))

    op.create_table(
        "invite_codes",
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("max_uses", sa.Integer(), nullable=False),
        sa.Column("uses", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["created_by"], ["user_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("code"),
        sa.CheckConstraint("uses <= max_uses", name="ck_invite_codes_uses_bound"),
    )

    op.create_table(
        "admin_audit_log",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("admin_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(length=60), nullable=False),
        sa.Column("target_type", sa.String(length=40), nullable=True),
        sa.Column("target_id", sa.String(length=80), nullable=True),
        sa.Column("details", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["admin_user_id"], ["user_profiles.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_admin_audit_log_created", "admin_audit_log", [sa.text("created_at DESC")])

    # --- admin bypass for RLS -----------------------------------------------
    #
    # SECURITY DEFINER, not a plain SQL function: without it, this function's
    # own lookup against user_profiles would itself be subject to the very
    # policy it is evaluating, from inside that policy's evaluation. It would
    # still terminate (the self-row match in every policy below is always
    # satisfiable for your own id), but there is no reason to rely on that
    # subtlety when running the check as the table owner sidesteps it
    # entirely. `SET search_path` pins it against search-path hijacking, the
    # standard caveat for any SECURITY DEFINER function.
    op.execute(
        """
        CREATE FUNCTION is_current_user_admin() RETURNS boolean
        LANGUAGE sql SECURITY DEFINER SET search_path = public STABLE AS $$
            SELECT EXISTS (
                SELECT 1 FROM user_profiles
                WHERE id = NULLIF(current_setting('app.user_id', true), '')::uuid
                AND role = 'admin'
            );
        $$
        """
    )

    op.execute("DROP POLICY user_profiles_owner ON user_profiles")
    op.execute(
        f"""
        CREATE POLICY user_profiles_owner ON user_profiles
        USING (id = {CURRENT_USER_ID_EXPR} OR is_current_user_admin())
        WITH CHECK (id = {CURRENT_USER_ID_EXPR} OR is_current_user_admin())
        """
    )

    for table in _ADMIN_READABLE_TABLES:
        op.execute(f"DROP POLICY {table}_owner ON {table}")
    op.execute(
        f"""
        CREATE POLICY user_saves_owner ON user_saves
        USING (user_id = {CURRENT_USER_ID_EXPR} OR is_current_user_admin())
        WITH CHECK (user_id = {CURRENT_USER_ID_EXPR})
        """
    )
    op.execute(
        f"""
        CREATE POLICY user_follows_owner ON user_follows
        USING (user_id = {CURRENT_USER_ID_EXPR} OR is_current_user_admin())
        WITH CHECK (user_id = {CURRENT_USER_ID_EXPR})
        """
    )
    op.execute(
        f"""
        CREATE POLICY impressions_owner ON impressions
        USING (user_id IS NULL OR user_id = {CURRENT_USER_ID_EXPR} OR is_current_user_admin())
        WITH CHECK (user_id IS NULL OR user_id = {CURRENT_USER_ID_EXPR})
        """
    )
    op.execute(
        f"""
        CREATE POLICY interaction_events_owner ON interaction_events
        USING (user_id IS NULL OR user_id = {CURRENT_USER_ID_EXPR} OR is_current_user_admin())
        WITH CHECK (user_id IS NULL OR user_id = {CURRENT_USER_ID_EXPR})
        """
    )

    # invite_codes and admin_audit_log are never read outside an admin-gated
    # route, but RLS here is what makes that true at the database too, not
    # only in application code.
    op.execute("ALTER TABLE invite_codes ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE invite_codes FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY invite_codes_admin_only ON invite_codes
        USING (is_current_user_admin())
        WITH CHECK (is_current_user_admin())
        """
    )
    op.execute("ALTER TABLE admin_audit_log ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE admin_audit_log FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY admin_audit_log_admin_only ON admin_audit_log
        USING (is_current_user_admin())
        WITH CHECK (is_current_user_admin())
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY admin_audit_log_admin_only ON admin_audit_log")
    op.execute("DROP POLICY invite_codes_admin_only ON invite_codes")

    op.execute("DROP POLICY interaction_events_owner ON interaction_events")
    op.execute(
        f"""
        CREATE POLICY interaction_events_owner ON interaction_events
        USING (user_id IS NULL OR user_id = {CURRENT_USER_ID_EXPR})
        WITH CHECK (user_id IS NULL OR user_id = {CURRENT_USER_ID_EXPR})
        """
    )
    op.execute("DROP POLICY impressions_owner ON impressions")
    op.execute(
        f"""
        CREATE POLICY impressions_owner ON impressions
        USING (user_id IS NULL OR user_id = {CURRENT_USER_ID_EXPR})
        WITH CHECK (user_id IS NULL OR user_id = {CURRENT_USER_ID_EXPR})
        """
    )
    op.execute("DROP POLICY user_follows_owner ON user_follows")
    op.execute(
        f"""
        CREATE POLICY user_follows_owner ON user_follows
        USING (user_id = {CURRENT_USER_ID_EXPR})
        WITH CHECK (user_id = {CURRENT_USER_ID_EXPR})
        """
    )
    op.execute("DROP POLICY user_saves_owner ON user_saves")
    op.execute(
        f"""
        CREATE POLICY user_saves_owner ON user_saves
        USING (user_id = {CURRENT_USER_ID_EXPR})
        WITH CHECK (user_id = {CURRENT_USER_ID_EXPR})
        """
    )

    op.execute("DROP POLICY user_profiles_owner ON user_profiles")
    op.execute(
        f"""
        CREATE POLICY user_profiles_owner ON user_profiles
        USING (id = {CURRENT_USER_ID_EXPR})
        WITH CHECK (id = {CURRENT_USER_ID_EXPR})
        """
    )

    op.execute("DROP FUNCTION is_current_user_admin()")

    op.drop_index("ix_admin_audit_log_created", table_name="admin_audit_log")
    op.drop_table("admin_audit_log")
    op.drop_table("invite_codes")

    op.drop_column("articles", "removed_reason")
    op.drop_column("articles", "removed_at")

    op.drop_constraint("ck_user_profiles_role", "user_profiles", type_="check")
    op.drop_column("user_profiles", "redeemed_invite_code")
    op.drop_column("user_profiles", "invite_redeemed_at")
    op.drop_column("user_profiles", "role")
