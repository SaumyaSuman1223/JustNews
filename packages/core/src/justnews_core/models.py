"""Database schema for the content pipeline (Stage 1).

Design notes that are not obvious from the column list:

* Topics are keyed by IPTC Media Topics **concept ID**, never by label. Labels
  live in ``topic_labels``, one row per language, so the same topic can be
  displayed in thirteen official languages plus any we supply ourselves
  (ADR 0006).
* ``articles.embedding`` is a 384-dimension ``halfvec``: 768 bytes rather than
  1536, which matters against a 500 MB free-tier budget (ADR 0003/0005).
* Near-duplicate articles are grouped into a ``story_cluster``. Because the
  embedding is multilingual, that clustering is cross-lingual by construction:
  the same event in English, Spanish and Arabic lands in one cluster.
* We store title, snippet, image URL, source, author and canonical link. There
  is deliberately no column for full article text and there must never be one.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar

from pgvector.sqlalchemy import HALFVEC, VECTOR
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from justnews_core.settings import get_settings

EMBEDDING_DIM = 384

# Which pgvector column type embeddings use. See Settings.vector_type for why
# this is configurable at all; it is a deployment-target compatibility flag,
# not a tuning knob, and the migration reads the same value so schema and model
# can never disagree.
EmbeddingVector = VECTOR if get_settings().vector_type == "vector" else HALFVEC

# The pgvector operator class must match the column type, or index creation
# fails at migration time with a message that does not mention either.
EMBEDDING_COSINE_OPS = "vector_cosine_ops" if EmbeddingVector is VECTOR else "halfvec_cosine_ops"


class Base(DeclarativeBase):
    type_annotation_map: ClassVar[dict[Any, Any]] = {dict[str, Any]: JSONB}


def _utcnow() -> Any:
    return func.now()


# --------------------------------------------------------------------------
# Taxonomy
# --------------------------------------------------------------------------


class Topic(Base):
    """One IPTC Media Topics concept.

    ``id`` is the IPTC concept ID (``medtop:20000170``). ``path`` holds the
    full ancestry root-first, so a level-4 concept is reachable from its
    level-1 ancestor with a single array containment query.
    """

    __tablename__ = "topics"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    parent_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("topics.id", ondelete="RESTRICT"), index=True
    )
    level: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    path: Mapped[list[str]] = mapped_column(ARRAY(String(32)), nullable=False)
    slug: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    labels: Mapped[list[TopicLabel]] = relationship(
        back_populates="topic", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (
        CheckConstraint("level between 1 and 5", name="ck_topics_level_range"),
        Index("ix_topics_path", "path", postgresql_using="gin"),
    )


class TopicLabel(Base):
    """Display name for a topic in one language.

    IPTC ships 13 languages. For anything it does not cover - Hindi, for
    instance - we add rows here rather than forking the taxonomy.
    """

    __tablename__ = "topic_labels"

    topic_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True
    )
    language: Mapped[str] = mapped_column(String(12), primary_key=True)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    is_official: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    topic: Mapped[Topic] = relationship(back_populates="labels")


# --------------------------------------------------------------------------
# Sources and feeds
# --------------------------------------------------------------------------


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    homepage_url: Mapped[str] = mapped_column(Text, nullable=False)
    country: Mapped[str | None] = mapped_column(String(2))
    language: Mapped[str] = mapped_column(String(12), nullable=False)
    trust_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=_utcnow()
    )

    feeds: Mapped[list[Feed]] = relationship(back_populates="source", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("trust_score between 0 and 1", name="ck_sources_trust_range"),
    )


class Feed(Base):
    """One RSS/Atom endpoint.

    ``etag`` and ``last_modified`` drive conditional GETs, which is how a
    15-minute poll over 400 feeds stays polite and cheap.
    ``consecutive_failures`` drives exponential backoff so one dead feed cannot
    slow the whole run.
    """

    __tablename__ = "feeds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    url: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    language: Mapped[str] = mapped_column(String(12), nullable=False)
    topic_hint_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("topics.id", ondelete="SET NULL")
    )
    etag: Mapped[str | None] = mapped_column(String(400))
    last_modified: Mapped[str | None] = mapped_column(String(120))
    last_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consecutive_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    source: Mapped[Source] = relationship(back_populates="feeds")

    __table_args__ = (Index("ix_feeds_active_last_fetched", "active", "last_fetched_at"),)


class SourceCategoryMap(Base):
    """Map a source's own category string onto an IPTC concept.

    Mapping is far cheaper and more accurate than classifying from scratch, so
    the pipeline maps first and only classifies what is left over (ADR 0006).
    Editable from the admin console in Stage 4.
    """

    __tablename__ = "source_category_map"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("sources.id", ondelete="CASCADE"), index=True
    )
    raw_category: Mapped[str] = mapped_column(String(200), nullable=False)
    topic_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False
    )

    __table_args__ = (UniqueConstraint("source_id", "raw_category", name="uq_source_category_map"),)


class Author(Base):
    __tablename__ = "authors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sources.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), nullable=False)

    __table_args__ = (UniqueConstraint("source_id", "slug", name="uq_authors_source_slug"),)


class Edition(Base):
    """A named regional/language view of the corpus, e.g. ``en-GB``."""

    __tablename__ = "editions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(12), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    language: Mapped[str] = mapped_column(String(12), nullable=False)
    country: Mapped[str | None] = mapped_column(String(2))
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


# --------------------------------------------------------------------------
# Content
# --------------------------------------------------------------------------


class StoryCluster(Base):
    """A group of near-duplicate articles covering one event.

    Cross-lingual by construction: the dedup layer compares multilingual
    embeddings, so the same story reported in three languages collapses here.
    """

    __tablename__ = "story_clusters"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    centroid: Mapped[Any | None] = mapped_column(EmbeddingVector(EMBEDDING_DIM))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    article_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    language_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (Index("ix_story_clusters_last_seen", "last_seen_at"),)


class Article(Base):
    """Headline metadata only.

    There is no ``body`` column and there must never be one: we store title,
    snippet, image URL, source, author and canonical link, and always link out
    to the publisher.
    """

    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    url_canonical: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    snippet: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(Text)

    source_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    feed_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("feeds.id", ondelete="SET NULL")
    )
    author_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("authors.id", ondelete="SET NULL")
    )
    story_cluster_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("story_clusters.id", ondelete="SET NULL"), index=True
    )

    language: Mapped[str] = mapped_column(String(12), nullable=False, index=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=_utcnow()
    )

    simhash: Mapped[int] = mapped_column(BigInteger, nullable=False)
    embedding: Mapped[Any | None] = mapped_column(EmbeddingVector(EMBEDDING_DIM))
    search_vector: Mapped[Any | None] = mapped_column(TSVECTOR)
    quality_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)

    __table_args__ = (
        Index("ix_articles_published_at_desc", published_at.desc()),
        Index("ix_articles_lang_published", "language", published_at.desc()),
        Index("ix_articles_search_vector", "search_vector", postgresql_using="gin"),
        Index("ix_articles_simhash", "simhash"),
        # Approximate-nearest-neighbour index over article embeddings.
        #
        # HNSW rather than IVFFlat: IVFFlat needs a populated table to pick sane
        # lists, and degrades under the heavy recency filtering this feed does,
        # where a query touches only the last few days of a much larger table.
        # HNSW builds incrementally, which suits a corpus that grows every
        # fifteen minutes and is pruned at ninety days.
        #
        # Declared here rather than as raw SQL in the migration so that
        # `alembic check` can see it - an index that exists only in a migration
        # reads as drift on every run, and real drift then hides in the noise.
        Index(
            "ix_articles_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": EMBEDDING_COSINE_OPS},
        ),
    )


class ArticleTopic(Base):
    __tablename__ = "article_topics"

    article_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True
    )
    topic_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    assigned_by: Mapped[str] = mapped_column(String(20), nullable=False, default="mapping")

    __table_args__ = (
        CheckConstraint("confidence between 0 and 1", name="ck_article_topics_confidence"),
        CheckConstraint(
            "assigned_by in ('mapping', 'classifier', 'feed_hint', 'manual')",
            name="ck_article_topics_assigned_by",
        ),
        Index("ix_article_topics_topic", "topic_id"),
    )


# --------------------------------------------------------------------------
# Operations
# --------------------------------------------------------------------------


class IngestRun(Base):
    """One pass of the ingestion job. The admin console reads this table."""

    __tablename__ = "ingest_runs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=_utcnow()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    trigger: Mapped[str] = mapped_column(String(20), nullable=False, default="cron")

    feeds_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    feeds_ok: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    feeds_not_modified: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    feeds_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    entries_seen: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    articles_new: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    articles_duplicate: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    articles_clustered: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    articles_enriched: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    gnews_calls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # A run that stopped at its own deadline is healthy; one that was killed is
    # not, and only a column can tell them apart after the fact.
    deadline_reached: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (Index("ix_ingest_runs_started", started_at.desc()),)


class ApiQuotaUsage(Base):
    """Daily spend against a rate-limited upstream, so we never blow the budget.

    GNews gives us 100 calls a day. Exceeding it is not a soft failure - the
    remaining calls simply return errors - so the budget is enforced here
    before a call is made, not discovered afterwards.
    """

    __tablename__ = "api_quota_usage"

    provider: Mapped[str] = mapped_column(String(40), primary_key=True)
    usage_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    calls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


# --------------------------------------------------------------------------
# Users and interactions (Stage 2)
# --------------------------------------------------------------------------
#
# RLS on these tables checks a plain session-local setting, ``app.user_id``,
# rather than Supabase's ``auth.uid()``. Browsers in this system never talk to
# Postgres directly - every request goes through the API, which verifies the
# JWT itself - so RLS here is defence in depth against a repository query that
# forgets a ``WHERE user_id = ...`` filter, not the primary authorization
# boundary. A plain session variable does that job identically in local dev,
# CI and Supabase, with no dependency on Supabase's auth schema (ADR 0007).
# ``core/db.py``'s ``session_scope_for_user`` is what sets it, once, at the
# start of an authenticated request's transaction.

CURRENT_USER_ID_EXPR = "NULLIF(current_setting('app.user_id', true), '')::uuid"


class UserProfile(Base):
    """The row Supabase's ``auth.users`` does not give us room to extend.

    Created lazily on a user's first authenticated request rather than via a
    trigger on ``auth.users`` - simpler, and this schema has no FK into an
    ``auth`` schema it does not own, so it works identically against Supabase
    and a local Postgres with no Supabase extension installed at all.
    """

    __tablename__ = "user_profiles"

    id: Mapped[Any] = mapped_column(UUID(as_uuid=True), primary_key=True)
    preferred_languages: Mapped[list[str]] = mapped_column(
        ARRAY(String(12)), nullable=False, default=list
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=_utcnow()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=_utcnow(), onupdate=_utcnow()
    )


class UserSave(Base):
    """A bookmark. Declarative, idempotent state - not an event log."""

    __tablename__ = "user_saves"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[Any] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False
    )
    article_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("articles.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=_utcnow()
    )

    __table_args__ = (
        UniqueConstraint("user_id", "article_id", name="uq_user_saves_user_article"),
        Index("ix_user_saves_user_created", "user_id", created_at.desc()),
    )


class UserFollow(Base):
    """A followed topic. Declarative state, same reasoning as ``UserSave``."""

    __tablename__ = "user_follows"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[Any] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False
    )
    topic_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=_utcnow()
    )

    __table_args__ = (
        UniqueConstraint("user_id", "topic_id", name="uq_user_follows_user_topic"),
        Index("ix_user_follows_user", "user_id"),
    )


class Impression(Base):
    """One item shown to one reader. The propensity column is the whole point:
    the probability the serving policy had of showing this item, written at
    serve time by the policy that made the decision. It cannot be
    reconstructed later, so nothing here is optional.

    ``user_id`` is nullable - an exploring, logged-out reader still generates
    impressions, keyed by ``session_id`` alone.
    """

    __tablename__ = "impressions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[Any | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="SET NULL")
    )
    session_id: Mapped[str] = mapped_column(String(64), nullable=False)
    article_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("articles.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    surface: Mapped[str] = mapped_column(String(16), nullable=False)
    locale: Mapped[str] = mapped_column(String(12), nullable=False)
    propensity: Mapped[float] = mapped_column(Float, nullable=False)
    served_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=_utcnow()
    )

    __table_args__ = (
        CheckConstraint("propensity between 0 and 1", name="ck_impressions_propensity_range"),
        CheckConstraint(
            "surface in ('feed', 'explore', 'search', 'topic')", name="ck_impressions_surface"
        ),
        Index("ix_impressions_user_served", "user_id", served_at.desc()),
        Index("ix_impressions_session_served", "session_id", served_at.desc()),
    )


class InteractionEvent(Base):
    """Something a reader did about an item they were shown: clicked it,
    saved it, marked it not interesting, or lingered without clicking.

    ``impression_id`` links the action back to the exact impression - same
    position, same propensity - that produced it, which is what makes the
    Stage 6 offline evaluators (IPS, doubly robust) exact rather than
    approximately joined after the fact.
    """

    __tablename__ = "interaction_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[Any | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="SET NULL")
    )
    session_id: Mapped[str] = mapped_column(String(64), nullable=False)
    article_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("articles.id", ondelete="CASCADE"), nullable=False
    )
    impression_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("impressions.id", ondelete="SET NULL")
    )
    event_type: Mapped[str] = mapped_column(String(20), nullable=False)
    position: Mapped[int | None] = mapped_column(SmallInteger)
    surface: Mapped[str] = mapped_column(String(16), nullable=False)
    locale: Mapped[str] = mapped_column(String(12), nullable=False)
    dwell_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=_utcnow()
    )

    __table_args__ = (
        CheckConstraint(
            "event_type in ('click', 'save', 'unsave', 'share', 'not_interested', 'dwell')",
            name="ck_interaction_events_type",
        ),
        CheckConstraint(
            "surface in ('feed', 'explore', 'search', 'topic')",
            name="ck_interaction_events_surface",
        ),
        Index(
            "ix_interaction_events_user_type_created", "user_id", "event_type", created_at.desc()
        ),
        Index("ix_interaction_events_article", "article_id"),
    )
