import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";

import { ArticleActions } from "@/components/ArticleActions";
import { ArticleCard } from "@/components/ArticleCard";
import { CoverageChips } from "@/components/CoverageChips";
import { FollowSourceButton } from "@/components/FollowSourceButton";
import { FeedList } from "@/components/FeedList";
import {
  getArticle,
  getArticleTopicLinks,
  getArticles,
  getFollowedSources,
  getSaves,
  getStory,
} from "@/lib/api";
import { curatedTopicLabel } from "@/lib/curatedTopics";
import { getBrowsingSessionId } from "@/lib/browsingSession";
import {
  formatRelativeTime,
  getLocale,
  isLocaleCode,
  locales,
  readerLanguages,
  t,
  tPlural,
} from "@/lib/i18n";
import { getSession } from "@/lib/session";

interface RouteParams {
  locale: string;
  id: string;
}

async function loadArticle(id: string) {
  const articleId = Number(id);
  if (!Number.isInteger(articleId)) return null;
  const result = await getArticle(articleId);
  return result.data;
}

export async function generateMetadata({
  params,
}: {
  params: Promise<RouteParams>;
}): Promise<Metadata> {
  const { id, locale } = await params;
  const article = await loadArticle(id);
  if (!article) {
    return { title: t(isLocaleCode(locale) ? locale : "en", "article.notFound") };
  }
  return {
    title: article.title,
    description: article.snippet ?? undefined,
    alternates: { canonical: `/${(await params).locale}/a/${article.id}` },
    // The publisher's own photo, used as-is - it isn't ours to alter. Falls
    // through to the generated default (opengraph-image.tsx) when an
    // article has none.
    ...(article.image_url && { openGraph: { images: [{ url: article.image_url }] } }),
  };
}

export default async function ArticleDetailPage({ params }: { params: Promise<RouteParams> }) {
  const { locale, id } = await params;
  if (!isLocaleCode(locale)) notFound();
  const active = getLocale(locale);

  const article = await loadArticle(id);
  if (!article) notFound();

  const [session, story, topics] = await Promise.all([
    getSession(),
    article.story_cluster_id
      ? getStory(article.story_cluster_id, active.code)
      : Promise.resolve(null),
    getArticleTopicLinks(article.id, active.code),
  ]);
  const filedUnder = topics.data.map((topic) => ({
    ...topic,
    label: curatedTopicLabel(topic.id, topic.label, active.code),
  }));
  const primaryTopic = filedUnder.find((topic) => topic.is_primary) ?? filedUnder[0] ?? null;

  // Checked against the most recent saves only - good enough for the common
  // case, and consistent with how every other page in this app checks it.
  const auth = session
    ? { accessToken: session.accessToken, sessionId: await getBrowsingSessionId() }
    : null;
  const saved = auth
    ? await getSaves(auth).then((page) =>
        page.data.items.some((item) => item.article.id === article.id),
      )
    : false;
  const followingSource = auth
    ? await getFollowedSources(auth).then((rows) =>
        rows.some((row) => row.source_id === article.source_id),
      )
    : false;

  const related = story?.data?.articles.filter((item) => item.id !== article.id) ?? [];

  // Fifth pass F4: this page is where search and shared links land, and it
  // used to end at the outbound button. What to read next comes from facts
  // about this article - its own topic, its own publisher - in the reader's
  // languages, never repeating the article itself or the story's other
  // reports already listed above.
  const shown = new Set([article.id, ...related.map((item) => item.id)]);
  // The reader's languages, plus the one this article is in - they are
  // already reading it, so it is a language they asked for.
  const readNextLanguages = [
    ...new Set([...readerLanguages(undefined, active.code).split(","), article.language]),
  ].join(",");
  const [inTopic, fromSource] = await Promise.all([
    primaryTopic
      ? getArticles({ languages: readNextLanguages, topic: primaryTopic.id, pageSize: 12 })
      : Promise.resolve(null),
    getArticles({ languages: readNextLanguages, source: article.source_id, pageSize: 8 }),
  ]);
  const moreInTopic = (inTopic?.data.items ?? [])
    .filter(
      (item) =>
        !shown.has(item.id) &&
        (article.story_cluster_id === null || item.story_cluster_id !== article.story_cluster_id),
    )
    .slice(0, 5);
  moreInTopic.forEach((item) => shown.add(item.id));
  const moreFromSource = fromSource.data.items.filter((item) => !shown.has(item.id)).slice(0, 4);
  // Only languages other than the one being read: telling someone the article
  // in front of them is available in the language it is written in is noise.
  const otherLanguages =
    story?.data?.coverage.filter((entry) => entry.language !== article.language) ?? [];

  // Same rule as the card: name the language, do not print its code.
  const foreign =
    article.language === active.code
      ? null
      : (locales.find((option) => option.code === article.language) ?? {
          label: article.language,
          htmlLang: article.language,
        });

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "NewsArticle",
    headline: article.title,
    description: article.snippet ?? undefined,
    image: article.image_url ?? undefined,
    datePublished: article.published_at,
    inLanguage: article.language,
    publisher: { "@type": "Organization", name: article.source_name },
    mainEntityOfPage: article.url,
  };

  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />

      <article className="article-header">
        <p className="card__meta">
          <Link
            className="card__source"
            href={`/${active.code}/source/${encodeURIComponent(article.source_slug)}`}
          >
            {article.source_name}
          </Link>
          <time dateTime={article.published_at}>
            {formatRelativeTime(article.published_at, active.code)}
          </time>
          {foreign && (
            <span className="badge" lang={foreign.htmlLang}>
              {foreign.label}
            </span>
          )}
        </p>
        <h1>{article.title}</h1>

        {article.image_url && (
          <Image
            className="article-media"
            src={article.image_url}
            alt=""
            width={1200}
            height={675}
            unoptimized
            priority
          />
        )}

        {article.snippet && <p className="article-snippet">{article.snippet}</p>}

        {filedUnder.length > 0 && (
          <p className="article-topics">
            <span className="article-topics__label">{t(active.code, "article.filedUnder")}</span>
            {filedUnder.map((topic) => (
              <Link
                key={topic.id}
                className="topic-chip"
                href={`/${active.code}/desk/${encodeURIComponent(topic.id)}`}
              >
                {topic.label}
              </Link>
            ))}
          </p>
        )}

        <div className="outbound-cta">
          <a
            className="button button--primary"
            href={article.url}
            target="_blank"
            rel="noopener noreferrer nofollow"
          >
            {t(active.code, "article.readFull", { source: article.source_name })}
          </a>
        </div>

        {session && (
          <div className="card__actions">
            <ArticleActions
              articleId={article.id}
              locale={active.code}
              surface="feed"
              saved={saved}
              revalidatePath={`/${active.code}/a/${article.id}`}
            />
            <FollowSourceButton
              sourceId={article.source_id}
              sourceName={article.source_name}
              locale={active.code}
              following={followingSource}
              revalidatePath={`/${active.code}/a/${article.id}`}
            />
          </div>
        )}
      </article>

      {otherLanguages.length > 0 && (
        <section className="callout" aria-labelledby="other-languages-heading">
          {/* The moment a reader notices this product does something unusual:
              the same event, being reported right now in a language they may
              not have thought to look in. */}
          <h2 id="other-languages-heading" className="coverage-group__heading">
            {tPlural(active.code, "article.otherLanguages", otherLanguages.length)}
          </h2>
          <CoverageChips coverage={otherLanguages} locale={active.code} />
        </section>
      )}

      {related.length > 0 && (
        <section aria-labelledby="related-heading">
          <h2 id="related-heading" className="related-heading">
            {tPlural(active.code, "article.otherSources", related.length)} ·{" "}
            <Link href={`/${active.code}/story/${article.story_cluster_id}`}>
              {t(active.code, "article.seeFullCoverage")}
            </Link>
          </h2>
          <ul className="feed">
            {related.map((item, index) => (
              <ArticleCard
                key={item.id}
                article={item}
                locale={active.code}
                surface="topic"
                position={index}
                signedIn={Boolean(session)}
                revalidatePath={`/${active.code}/a/${article.id}`}
              />
            ))}
          </ul>
        </section>
      )}

      {primaryTopic && moreInTopic.length > 0 && (
        <section className="read-next" aria-labelledby="more-in-topic">
          <h2 id="more-in-topic" className="home-tier">
            <Link href={`/${active.code}/desk/${encodeURIComponent(primaryTopic.id)}`}>
              {t(active.code, "article.moreIn", { topic: primaryTopic.label })}
            </Link>
          </h2>
          <FeedList
            items={moreInTopic.map((item) => ({ article: item }))}
            locale={active.code}
            surface="topic"
            signedIn={Boolean(session)}
            revalidatePath={`/${active.code}/a/${article.id}`}
            layout="list"
          />
        </section>
      )}

      {moreFromSource.length > 0 && (
        <section className="read-next" aria-labelledby="more-from-source">
          <h2 id="more-from-source" className="home-tier">
            <Link href={`/${active.code}/source/${encodeURIComponent(article.source_slug)}`}>
              {t(active.code, "article.moreFrom", { source: article.source_name })}
            </Link>
          </h2>
          <FeedList
            items={moreFromSource.map((item) => ({ article: item }))}
            locale={active.code}
            surface="topic"
            signedIn={Boolean(session)}
            revalidatePath={`/${active.code}/a/${article.id}`}
            layout="list"
          />
        </section>
      )}

      <p className="form-note">
        <Link href={`/${active.code}`}>{t(active.code, "article.backToFront")}</Link>
      </p>
    </>
  );
}
