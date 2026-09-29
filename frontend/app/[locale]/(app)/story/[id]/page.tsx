import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";

import { StoryCoverage, type CoverageColumn } from "@/components/discover/StoryCoverage";
import { CoverageChips } from "@/components/CoverageChips";
import { FollowStoryButton } from "@/components/FollowStoryButton";
import { Perspectives } from "@/components/Perspectives";
import {
  getStory,
  getStoryFollowState,
  getTopicStories,
  markStorySeen,
  type StoryDetail,
} from "@/lib/api";
import { getBrowsingSessionId } from "@/lib/browsingSession";
import { curatedTopicLabel } from "@/lib/curatedTopics";
import { viewHref } from "@/lib/discoverView";
import { formatRelativeTime, getLocale, isLocaleCode, locales, t, tPlural } from "@/lib/i18n";
import { getSession } from "@/lib/session";

interface RouteParams {
  locale: string;
  id: string;
}

/**
 * The report that speaks for the story on this page: the first one in the
 * reader's interface language, or the first report at all. Its headline is
 * the page's title and its snippet the standfirst - a Hindi reader of a
 * story first reported in English gets the Hindi headline, tagged as Hindi.
 */
function voiceOf(detail: StoryDetail, locale: string) {
  const inLocale = detail.articles.find((article) => article.language === locale);
  const first = detail.articles[0];
  const voice = inLocale ?? first;
  return {
    title: voice?.title ?? detail.story.title,
    language: voice?.language ?? first?.language,
    snippet: voice?.snippet ?? null,
    image: (voice?.image_url ? voice : detail.articles.find((article) => article.image_url))
      ?.image_url,
  };
}

async function loadStory(id: string, language: string) {
  const storyId = Number(id);
  if (!Number.isInteger(storyId)) return null;
  const result = await getStory(storyId, language);
  return result.data;
}

export async function generateMetadata({
  params,
}: {
  params: Promise<RouteParams>;
}): Promise<Metadata> {
  const { locale, id } = await params;
  const active = isLocaleCode(locale) ? locale : "en";
  const detail = await loadStory(id, active);
  if (!detail) {
    return { title: t(active, "article.notFound") };
  }
  const voice = voiceOf(detail, active);
  const leadImage = voice.image;
  return {
    title: voice.title,
    description: voice.snippet ?? undefined,
    alternates: { canonical: `/${locale}/story/${detail.story.id}` },
    // The lead article's own photo - same reasoning as the article page:
    // falls through to the generated default when there isn't one.
    ...(leadImage && { openGraph: { images: [{ url: leadImage }] } }),
  };
}

/**
 * The coverage view (frontend spec §37): every source on this story, across
 * languages, plus how it developed - never the publisher's own text. This
 * page is the honest alternative to "read the article here" that CLAUDE.md's
 * data rules force: JustNews stores a title, a snippet and a link, never a
 * body, so there is no full article to render in its place.
 *
 * Deliberately absent: a "why this matters" explainer. The direction
 * document's mockup shows one, but writing it would mean either an editorial
 * voice this product doesn't have or a model call in the request path (ADR
 * 0004 forbids exactly that) - a confident-sounding paragraph with no real
 * author behind it is worse than not having the section.
 */
export default async function StoryPage({ params }: { params: Promise<RouteParams> }) {
  const { locale, id } = await params;
  if (!isLocaleCode(locale)) notFound();
  const active = getLocale(locale);

  const detail = await loadStory(id, active.code);
  if (!detail) notFound();

  const [session, related] = await Promise.all([
    getSession(),
    detail.category
      ? getTopicStories(detail.category.id, 6).then((page) =>
          page.data.filter((story) => story.id !== detail.story.id).slice(0, 5),
        )
      : Promise.resolve([]),
  ]);
  const auth = session
    ? { accessToken: session.accessToken, sessionId: await getBrowsingSessionId() }
    : null;
  const following = auth ? await getStoryFollowState(auth, detail.story.id) : null;
  // Opening the story is what "seen" means for "N new reports since you
  // looked" (fifth pass F2) - so a follower's visit resets their count.
  if (auth && following) await markStorySeen(auth, detail.story.id);

  const voice = voiceOf(detail, active.code);
  const titleLang = locales.find((option) => option.code === voice.language)?.htmlLang;
  const category = detail.category
    ? {
        ...detail.category,
        label: curatedTopicLabel(detail.category.id, detail.category.label, active.code),
      }
    : null;

  // Grouped by language rather than listed flat: the point of this page is
  // that the same event reads differently depending on where it is reported
  // from, and a flat list buries that. The reader's own language leads; the
  // rest follow the coverage breakdown, most-covered first.
  const order = [
    ...detail.coverage.filter((entry) => entry.language === active.code),
    ...detail.coverage.filter((entry) => entry.language !== active.code),
  ].map((entry) => entry.language);
  const columns: CoverageColumn[] = order.map((language) => ({
    language,
    label: locales.find((locale) => locale.code === language)?.label ?? language,
    htmlLang: locales.find((locale) => locale.code === language)?.htmlLang ?? language,
    articles: detail.articles.filter((article) => article.language === language),
  }));

  return (
    <>
      <div className="page-header story-header">
        <h1 lang={titleLang}>{voice.title}</h1>
        {voice.snippet && (
          <p className="article-snippet" lang={titleLang}>
            {voice.snippet}
          </p>
        )}
        {/* Reports and sources counted separately: one outlet filing twice
            is two reports from one source, and saying only "1 source" beside
            a count of 2 read as a contradiction. */}
        <p>
          {[
            tPlural(active.code, "story.reports", detail.articles.length),
            tPlural(active.code, "coverage.sources", detail.story.source_count),
            ...(detail.story.language_count > 1
              ? [tPlural(active.code, "coverage.languages", detail.story.language_count)]
              : []),
          ].join(" · ")}
        </p>
        <p className="story-header__facts">
          {category && (
            <>
              <Link href={viewHref(active.code, { kind: "topic", topicId: category.id })}>
                {category.label}
              </Link>
              {" · "}
            </>
          )}
          {t(active.code, "story.firstReported", {
            time: formatRelativeTime(detail.story.first_seen_at, active.code),
          })}
          {" · "}
          {t(active.code, "story.lastUpdated", {
            time: formatRelativeTime(detail.story.last_seen_at, active.code),
          })}
        </p>
        {/* One language says nothing the line above does not. */}
        {detail.story.language_count > 1 && (
          <CoverageChips
            coverage={detail.coverage}
            locale={active.code}
            linkTo={(language) => `#coverage-${language}`}
          />
        )}
        {/* Null when it cannot be known (signed out, no beta access): no
            control at all rather than one that cannot work. */}
        {following !== null && (
          <div className="story-header__actions">
            <FollowStoryButton
              storyId={detail.story.id}
              locale={active.code}
              following={following}
              revalidatePath={`/${active.code}/story/${detail.story.id}`}
            />
          </div>
        )}
      </div>

      {voice.image && (
        <Image
          className="article-media story-media"
          src={voice.image}
          alt=""
          width={1200}
          sizes="(max-width: 48rem) 100vw, 44rem"
          height={675}
          priority
        />
      )}

      {/* This page is the story's coverage, laid out to compare: who
          reported it, in which language, and when - each report opening at
          its publisher. */}
      <StoryCoverage locale={active.code} columns={columns} />

      {detail.perspectives.length > 0 && (
        <section className="coverage-group">
          <h2 className="coverage-group__heading">
            {t(active.code, "story.perspectives.heading")}
          </h2>
          <Perspectives groups={detail.perspectives} locale={active.code} />
        </section>
      )}

      {related.length > 0 && (
        <section className="coverage-group">
          <h2 className="coverage-group__heading">{t(active.code, "story.related.heading")}</h2>
          <ul className="related-topics">
            {related.map((story) => (
              <li key={story.id}>
                <Link href={`/${active.code}/story/${story.id}`}>{story.title}</Link>
              </li>
            ))}
          </ul>
        </section>
      )}
    </>
  );
}
