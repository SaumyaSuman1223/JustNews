import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";

import { ArticleCard } from "@/components/ArticleCard";
import { CoverageChips } from "@/components/CoverageChips";
import { Perspectives } from "@/components/Perspectives";
import { getSaves, getStory, getTopicStories } from "@/lib/api";
import { getBrowsingSessionId } from "@/lib/browsingSession";
import { formatRelativeTime, getLocale, isLocaleCode, locales, t, tPlural } from "@/lib/i18n";
import { getSession } from "@/lib/session";

interface RouteParams {
  locale: string;
  id: string;
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
  const leadImage = detail.articles[0]?.image_url;
  return {
    title: detail.story.title,
    description: detail.articles[0]?.snippet ?? undefined,
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
  const savedIds = session
    ? await getSaves({
        accessToken: session.accessToken,
        sessionId: await getBrowsingSessionId(),
      }).then((page) => new Set(page.data.items.map((item) => item.article.id)))
    : new Set<number>();

  // The lead article - earliest reported, since list_articles_in_cluster
  // orders that way - stands in for the story's own image and standfirst.
  // Not an editorial pick, just the article that got here first.
  const lead = detail.articles[0];

  // Grouped by language rather than listed flat: the point of this page is
  // that the same event reads differently depending on where it is reported
  // from, and a flat list buries that. Ordered by the coverage breakdown, so
  // the language carrying the story leads.
  const order = detail.coverage.map((entry) => entry.language);
  const byLanguage = order.map((language) => ({
    language,
    label: locales.find((locale) => locale.code === language)?.label ?? language,
    htmlLang: locales.find((locale) => locale.code === language)?.htmlLang ?? language,
    articles: detail.articles.filter((article) => article.language === language),
  }));

  let position = 0;

  return (
    <>
      <div className="page-header story-header">
        {detail.category && <p className="eyebrow">{detail.category.label}</p>}
        <h1>{detail.story.title}</h1>
        {lead?.snippet && <p className="article-snippet">{lead.snippet}</p>}
        <p>
          {tPlural(active.code, "story.coveredBy", detail.story.source_count)}
          {detail.story.language_count > 1 &&
            ` ${t(active.code, "story.reportedIn", { count: detail.story.language_count })}`}
        </p>
        <p className="story-header__facts">
          {t(active.code, "story.firstReported", {
            time: formatRelativeTime(detail.story.first_seen_at, active.code),
          })}
          {" · "}
          {t(active.code, "story.lastUpdated", {
            time: formatRelativeTime(detail.story.last_seen_at, active.code),
          })}
        </p>
        <CoverageChips coverage={detail.coverage} locale={active.code} />
      </div>

      {lead?.image_url && (
        <Image
          className="article-media"
          src={lead.image_url}
          alt=""
          width={1200}
          height={675}
          unoptimized
          priority
        />
      )}

      {byLanguage.map((group) => (
        <section key={group.language} className="coverage-group">
          <h2 className="coverage-group__heading">
            <span lang={group.htmlLang}>{group.label}</span>
            <span className="coverage-group__count">
              {tPlural(active.code, "story.reports", group.articles.length)}
            </span>
          </h2>
          <ul className="feed">
            {group.articles.map((article) => (
              <ArticleCard
                key={article.id}
                article={article}
                locale={active.code}
                surface="topic"
                position={position++}
                signedIn={Boolean(session)}
                saved={savedIds.has(article.id)}
                revalidatePath={`/${active.code}/story/${detail.story.id}`}
              />
            ))}
          </ul>
        </section>
      ))}

      {detail.perspectives.length > 0 && (
        <section className="coverage-group">
          <h2 className="coverage-group__heading">{t(active.code, "desk.tabs.perspectives")}</h2>
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
