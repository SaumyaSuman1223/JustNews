import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";

import { ArticleActions } from "@/components/ArticleActions";
import { ArticleCard } from "@/components/ArticleCard";
import { CoverageChips } from "@/components/CoverageChips";
import { FollowSourceButton } from "@/components/FollowSourceButton";
import { getArticle, getFollowedSources, getSaves, getStory } from "@/lib/api";
import { getBrowsingSessionId } from "@/lib/browsingSession";
import { formatRelativeTime, getLocale, isLocaleCode, locales, t, tPlural } from "@/lib/i18n";
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

  const [session, story] = await Promise.all([
    getSession(),
    article.story_cluster_id ? getStory(article.story_cluster_id) : Promise.resolve(null),
  ]);

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
          <span>{article.source_name}</span>
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

      <p className="form-note">
        <Link href={`/${active.code}`}>{t(active.code, "article.backToFront")}</Link>
      </p>
    </>
  );
}
