"""Which image URLs are pictures of the story.

Feeds hand over more than photographs. Media enclosures are videos as often
as images (El País attaches its `.mp4`), a link can be a YouTube watch page,
and some publishers send one site-wide logo for every article that has no
photo of its own (The Hindu's `og-image.png`). Shown on a card, the first two
are a broken image and the third is the same crest on every story. So an
image is kept only if it can be one, and a source's picture is dropped once it
turns up on several of its articles - that is its placeholder, not a photo.
"""

from __future__ import annotations

from collections import Counter
from typing import Any
from urllib.parse import urlsplit

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.logging import get_logger
from justnews_core.models import Article

log = get_logger(__name__)

#: A picture a source has put on this many of its articles is its default,
#: not a photograph of any one of them.
PLACEHOLDER_REPEATS = 3

_NOT_IMAGES = (".mp4", ".m4v", ".mov", ".webm", ".m3u8", ".mpd", ".mp3", ".m4a", ".wav", ".ogg")
_VIDEO_HOSTS = ("youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be", "vimeo.com")


def usable_image_url(url: str | None) -> str | None:
    """`url` if it can be an image a card shows; None otherwise."""
    if not url:
        return None
    parts = urlsplit(url.strip())
    if parts.scheme not in ("http", "https") or not parts.netloc:
        return None
    if parts.netloc.lower() in _VIDEO_HOSTS:
        return None
    if parts.path.lower().endswith(_NOT_IMAGES):
        return None
    return url.strip()


async def placeholder_images(session: AsyncSession, source_id: int, urls: list[str]) -> set[str]:
    """Of `urls` about to be stored for one source, the ones that are its
    placeholder: already on, or about to be on, `PLACEHOLDER_REPEATS` of its
    articles. One query for the whole batch."""
    if not urls:
        return set()
    batch = Counter(urls)
    stored = dict(
        (
            await session.execute(
                select(Article.image_url, func.count())
                .where(Article.source_id == source_id, Article.image_url.in_(set(urls)))
                .group_by(Article.image_url)
            )
        )
        .tuples()
        .all()
    )
    return {
        url for url, count in batch.items() if count + stored.get(url, 0) >= PLACEHOLDER_REPEATS
    }


async def repair_images(session: AsyncSession, *, dry_run: bool = False) -> dict[str, Any]:
    """Clear stored image URLs that are not pictures of their story: videos
    and watch pages, and any picture a source repeats across
    `PLACEHOLDER_REPEATS` or more of its articles. Idempotent."""
    repeated = (
        await session.execute(
            select(Article.source_id, Article.image_url, func.count())
            .where(Article.image_url.is_not(None))
            .group_by(Article.source_id, Article.image_url)
            .having(func.count() >= PLACEHOLDER_REPEATS)
        )
    ).all()
    placeholders = sum(count for _, _, count in repeated)

    candidates = (
        await session.execute(
            select(Article.id, Article.image_url).where(Article.image_url.is_not(None))
        )
    ).all()
    unusable = [article_id for article_id, url in candidates if usable_image_url(url) is None]

    if not dry_run:
        for source_id, url, _ in repeated:
            await session.execute(
                update(Article)
                .where(Article.source_id == source_id, Article.image_url == url)
                .values(image_url=None)
            )
        if unusable:
            await session.execute(
                update(Article).where(Article.id.in_(unusable)).values(image_url=None)
            )
        await session.commit()
    report = {
        "dry_run": dry_run,
        "placeholder_images": len(repeated),
        "articles_with_a_placeholder": placeholders,
        "articles_with_a_non_image": len(unusable),
        "examples": [url for _, url, _ in repeated[:5]],
    }
    log.info("images_repaired", **{k: v for k, v in report.items() if k != "examples"})
    return report
