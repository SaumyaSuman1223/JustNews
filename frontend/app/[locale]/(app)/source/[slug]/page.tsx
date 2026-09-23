import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { EmptyState } from "@/components/EmptyState";
import { FeedList } from "@/components/FeedList";
import { FollowSourceButton } from "@/components/FollowSourceButton";
import { Pagination } from "@/components/Pagination";
import { getArticles, getFollowedSources, getSaves, getSource } from "@/lib/api";
import { getBrowsingSessionId } from "@/lib/browsingSession";
import { getLocale, isLocaleCode, locales, t, tPlural, type LocaleCode } from "@/lib/i18n";
import { getSession } from "@/lib/session";

/** ADR 0013's roles - the same six labels Perspectives groups by; "wire" is
 * not a perspective and is not labelled as one here either. */
const ROLE_LABEL_KEY = {
  industry: "desk.perspectives.role.industry",
  government: "desk.perspectives.role.government",
  academic: "desk.perspectives.role.academic",
  investor: "desk.perspectives.role.investor",
  consumer: "desk.perspectives.role.consumer",
  public: "desk.perspectives.role.public",
} as const;

interface RouteParams {
  locale: string;
  slug: string;
}

export async function generateMetadata({
  params,
}: {
  params: Promise<RouteParams>;
}): Promise<Metadata> {
  const { locale, slug } = await params;
  const source = (await getSource(decodeURIComponent(slug))).data;
  const code: LocaleCode = isLocaleCode(locale) ? locale : "en";
  if (!source) return { title: t(code, "source.notFound") };
  return {
    title: source.name,
    alternates: { canonical: `/${locale}/source/${encodeURIComponent(source.slug)}` },
  };
}

/**
 * A publisher's own page (fifth pass F3): who they are, and their latest
 * reporting in this corpus, newest first. Every byline in the product links
 * here - before this there was nowhere for "follow this source" to land.
 *
 * The facts shown are the source row's own: country, language, the editorial
 * role an admin assigned (ADR 0013), and a live article count. Nothing about
 * how "reliable" a publisher is - trust_score stays internal to ranking.
 */
export default async function SourcePage({
  params,
  searchParams,
}: {
  params: Promise<RouteParams>;
  searchParams: Promise<{ cursor?: string }>;
}) {
  const { locale, slug } = await params;
  if (!isLocaleCode(locale)) notFound();
  const active = getLocale(locale);
  const { cursor } = await searchParams;

  const source = (await getSource(decodeURIComponent(slug))).data;
  if (!source) notFound();

  const session = await getSession();
  const auth = session
    ? { accessToken: session.accessToken, sessionId: await getBrowsingSessionId() }
    : null;
  const basePath = `/${active.code}/source/${encodeURIComponent(source.slug)}`;

  const [articles, following, savedIds] = await Promise.all([
    getArticles({ source: source.id, cursor, pageSize: 24 }),
    auth
      ? getFollowedSources(auth).then((rows) => rows.some((row) => row.source_id === source.id))
      : Promise.resolve(false),
    auth
      ? getSaves(auth).then((page) => new Set(page.data.items.map((item) => item.article.id)))
      : Promise.resolve(new Set<number>()),
  ]);

  const roleKey = source.source_role
    ? ROLE_LABEL_KEY[source.source_role as keyof typeof ROLE_LABEL_KEY]
    : undefined;
  const language = locales.find((option) => option.code === source.language);
  const country = source.country
    ? new Intl.DisplayNames([active.code], { type: "region" }).of(source.country)
    : null;
  // Only facts the row actually has; a source with no recorded country or
  // role prints fewer items rather than a placeholder.
  const facts = [roleKey ? t(active.code, roleKey) : null, country, language?.label ?? null].filter(
    (fact): fact is string => Boolean(fact),
  );

  return (
    <>
      <header className="page-header source-header">
        <p className="eyebrow">{t(active.code, "source.eyebrow")}</p>
        <h1>{source.name}</h1>
        {facts.length > 0 && <p className="source-header__facts">{facts.join(" · ")}</p>}
        <p className="source-header__count">
          {tPlural(active.code, "source.articleCount", source.article_count)}
        </p>
        <div className="source-header__actions">
          <a
            className="button button--secondary"
            href={source.homepage_url}
            target="_blank"
            rel="noopener noreferrer nofollow"
          >
            {t(active.code, "source.visit", { source: source.name })}
          </a>
          {auth && (
            <FollowSourceButton
              sourceId={source.id}
              sourceName={source.name}
              locale={active.code}
              following={following}
              revalidatePath={basePath}
            />
          )}
        </div>
      </header>

      {articles.data.items.length === 0 ? (
        <EmptyState
          title={t(active.code, "source.empty.title", { source: source.name })}
          body={t(active.code, "source.empty.body")}
          action={{ href: `/${active.code}`, label: t(active.code, "article.backToFront") }}
        />
      ) : (
        <>
          <h2 className="home-tier">{t(active.code, "source.latest")}</h2>
          <FeedList
            items={articles.data.items.map((article) => ({
              article,
              saved: savedIds.has(article.id),
            }))}
            locale={active.code}
            surface="topic"
            signedIn={Boolean(session)}
            revalidatePath={basePath}
            layout="list"
          />
          <Pagination
            locale={active.code}
            baseHref={basePath}
            nextCursor={articles.data.next_cursor}
            onLaterPage={Boolean(cursor)}
          />
        </>
      )}
    </>
  );
}
