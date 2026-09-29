"""Which image URLs are kept: pictures yes; videos, watch pages and a
source's repeated placeholder no."""

from __future__ import annotations

from justnews_testing.factories import make_article, make_source
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.models import Article
from justnews_ingestion.images import placeholder_images, repair_images, usable_image_url


class TestUsableImageUrl:
    def test_keeps_a_picture(self) -> None:
        url = "https://ichef.bbci.co.uk/ace/standard/240/cpsprodpb/a.jpg"
        assert usable_image_url(url) == url

    def test_drops_videos_and_watch_pages(self) -> None:
        assert usable_image_url("https://vdmedia.elpais.com/x/1219253_video_1800.mp4") is None
        assert usable_image_url("https://www.youtube.com/watch?v=7LaH1dfjRG8") is None
        assert usable_image_url("https://cdn.example/stream/index.m3u8") is None

    def test_drops_a_host_that_refuses_embedding(self) -> None:
        url = "https://c.ndtvimg.com/2026-09/x_625x300.jpg?im=FeatureCrop,width=1280"
        assert usable_image_url(url) is None

    def test_drops_what_is_not_a_web_url(self) -> None:
        assert usable_image_url("data:image/png;base64,AAAA") is None
        assert usable_image_url("/relative/picture.jpg") is None
        assert usable_image_url("") is None
        assert usable_image_url(None) is None


class TestPlaceholders:
    async def test_a_picture_on_several_articles_is_the_placeholder(
        self, session: AsyncSession
    ) -> None:
        source = await make_source(session, slug="the-hindu")
        crest = "https://www.thehindu.com/theme/images/og-image.png"
        for index in range(2):
            await make_article(session, source, title=f"Story {index}", image_url=crest)
        await session.commit()

        found = await placeholder_images(
            session, source.id, [crest, "https://th-i.thgim.com/a/photo.jpg"]
        )
        assert found == {crest}

    async def test_another_source_using_the_url_does_not_count(self, session: AsyncSession) -> None:
        one = await make_source(session, slug="one")
        other = await make_source(session, slug="other")
        shared = "https://cdn.example/wire-photo.jpg"
        for index in range(3):
            await make_article(session, other, title=f"Wire {index}", image_url=shared)
        await session.commit()

        assert await placeholder_images(session, one.id, [shared]) == set()


class TestRepairImages:
    async def test_clears_placeholders_and_non_images(self, session: AsyncSession) -> None:
        source = await make_source(session, slug="the-hindu")
        crest = "https://www.thehindu.com/theme/images/og-image.png"
        for index in range(3):
            await make_article(session, source, title=f"Crest {index}", image_url=crest)
        video = await make_article(
            session, source, title="A video", image_url="https://cdn.example/clip.mp4"
        )
        photo = await make_article(
            session, source, title="A photo", image_url="https://cdn.example/photo.jpg"
        )
        await session.commit()

        dry = await repair_images(session, dry_run=True)
        assert dry["articles_with_a_placeholder"] == 3
        assert dry["articles_with_a_non_image"] == 1

        await repair_images(session)
        images = dict((await session.execute(select(Article.id, Article.image_url))).tuples().all())
        assert images[video.id] is None
        assert images[photo.id] == "https://cdn.example/photo.jpg"
        assert sum(1 for url in images.values() if url == crest) == 0
