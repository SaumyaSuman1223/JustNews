"""user profiles, saves, follows, impressions and interaction events

Revision ID: 0003_users_and_interactions
Revises: 0002_ingest_run_outcome
Create Date: 2026-09-01 00:00:00.000000+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from justnews_core.models import CURRENT_USER_ID_EXPR

revision: str = "0003_users_and_interactions"
down_revision: str | None = "0002_ingest_run_outcome"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Tables an owning user reads and writes, keyed off ``user_id``/``id``.
_OWNER_KEYED_TABLES = ("user_saves", "user_follows", "impressions", "interaction_events")


def upgrade() -> None:
    op.create_table(
        "user_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "preferred_languages",
            postgresql.ARRAY(sa.String(length=12)),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "user_saves",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("article_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "article_id", name="uq_user_saves_user_article"),
    )
    op.create_index(
        "ix_user_saves_user_created", "user_saves", ["user_id", sa.text("created_at DESC")]
    )

    op.create_table(
        "user_follows",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("topic_id", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "topic_id", name="uq_user_follows_user_topic"),
    )
    op.create_index("ix_user_follows_user", "user_follows", ["user_id"])

    op.create_table(
        "impressions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("article_id", sa.BigInteger(), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("surface", sa.String(length=16), nullable=False),
        sa.Column("locale", sa.String(length=12), nullable=False),
        sa.Column("propensity", sa.Float(), nullable=False),
        sa.Column(
            "served_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("propensity between 0 and 1", name="ck_impressions_propensity_range"),
        sa.CheckConstraint(
            "surface in ('feed', 'explore', 'search', 'topic')", name="ck_impressions_surface"
        ),
    )
    op.create_index(
        "ix_impressions_user_served", "impressions", ["user_id", sa.text("served_at DESC")]
    )
    op.create_index(
        "ix_impressions_session_served", "impressions", ["session_id", sa.text("served_at DESC")]
    )

    op.create_table(
        "interaction_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("article_id", sa.BigInteger(), nullable=False),
        sa.Column("impression_id", sa.BigInteger(), nullable=True),
        sa.Column("event_type", sa.String(length=20), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=True),
        sa.Column("surface", sa.String(length=16), nullable=False),
        sa.Column("locale", sa.String(length=12), nullable=False),
        sa.Column("dwell_ms", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["impression_id"], ["impressions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "event_type in ('click', 'save', 'unsave', 'share', 'not_interested', 'dwell')",
            name="ck_interaction_events_type",
        ),
        sa.CheckConstraint(
            "surface in ('feed', 'explore', 'search', 'topic')",
            name="ck_interaction_events_surface",
        ),
    )
    op.create_index(
        "ix_interaction_events_user_type_created",
        "interaction_events",
        ["user_id", "event_type", sa.text("created_at DESC")],
    )
    op.create_index("ix_interaction_events_article", "interaction_events", ["article_id"])

    # --- row level security -------------------------------------------------
    #
    # Defence in depth, not the primary authorization boundary: the API
    # verifies the caller's JWT and always queries as itself, never as the
    # end user's own Postgres role. ``app.user_id`` is a plain session-local
    # setting the API writes once per authenticated request
    # (``justnews_core.db.set_current_user``) - not Supabase's ``auth.uid()``,
    # which only exists when PostgREST calls this database directly. See
    # ADR 0007. Alembic's autogenerate diff does not inspect RLS state, so
    # this is raw SQL rather than a model annotation - there is nothing to
    # keep in sync on the model side.
    # FORCE, not just ENABLE: the migration and the API connect as the same
    # role, which owns these tables, and Postgres exempts a table's owner from
    # RLS unless forced - "enabled" alone would make this defence in depth a
    # no-op for the one role that actually queries these tables.
    op.execute("ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE user_profiles FORCE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY user_profiles_owner ON user_profiles
        USING (id = {CURRENT_USER_ID_EXPR})
        WITH CHECK (id = {CURRENT_USER_ID_EXPR})
        """
    )

    for table in _OWNER_KEYED_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

    # user_saves / user_follows always carry a real owner.
    for table in ("user_saves", "user_follows"):
        op.execute(
            f"""
            CREATE POLICY {table}_owner ON {table}
            USING (user_id = {CURRENT_USER_ID_EXPR})
            WITH CHECK (user_id = {CURRENT_USER_ID_EXPR})
            """
        )

    # impressions / interaction_events also cover logged-out sessions, where
    # user_id is NULL by design - those rows carry no per-user access check
    # beyond RLS being enabled at all, since there is no user to own them yet.
    for table in ("impressions", "interaction_events"):
        op.execute(
            f"""
            CREATE POLICY {table}_owner ON {table}
            USING (user_id IS NULL OR user_id = {CURRENT_USER_ID_EXPR})
            WITH CHECK (user_id IS NULL OR user_id = {CURRENT_USER_ID_EXPR})
            """
        )


def downgrade() -> None:
    op.drop_table("interaction_events")
    op.drop_table("impressions")
    op.drop_table("user_follows")
    op.drop_table("user_saves")
    op.drop_table("user_profiles")
