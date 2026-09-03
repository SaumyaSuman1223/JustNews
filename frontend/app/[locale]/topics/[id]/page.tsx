import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { EmptyState } from "@/components/EmptyState";
import { FeedList } from "@/components/FeedList";
import { Pagination } from "@/components/Pagination";
import { getArticles, getMe, getSaves, getTopics } from "@/lib/api";
import { getBrowsingSessionId } from "@/lib/browsingSession";
import { getLocale, isLocaleCode, readerLanguages, t } from "@/lib/i18n";
import { getSession } from "@/lib/session";

interface RouteParams {
  locale: string;
  id: string;
}

export async function generateMetadata({
  params,
}: {
  params: Promise<RouteParams>;
}): Promise<Metadata> {
  const { locale, id } = await params;
  const topicId = decodeURIComponent(id);
  const topics = await getTopics(isLocaleCode(locale) ? locale : "en");
  const topic = topics.data.find((item) => item.id === topicId);
  if (!topic) {
    return { title: t(isLocaleCode(locale) ? locale : "en", "topics.fallbackTitle") };
  }
  return {
    title: topic.label,
    alternates: { canonical: `/${locale}/topics/${encodeURIComponent(topic.id)}` },
  };
}

export default async function TopicDetailPage({
  params,
  searchParams,
}: {
  params: Promise<RouteParams>;
  searchParams: Promise<{ cursor?: string }>;
}) {
  const { locale, id } = await params;
  if (!isLocaleCode(locale)) notFound();
  const active = getLocale(locale);
  const { cursor } = await searchParams;
  // The topic id contains a colon (medtop:01000000) - encoded when this page
  // is linked to, and not every router stage decodes it back automatically.
  const topicId = decodeURIComponent(id);

  const session = await getSession();
  const auth = session
    ? { accessToken: session.accessToken, sessionId: await getBrowsingSessionId() }
    : null;
  const profile = auth ? await getMe(auth) : null;

  const [topics, articles, savedIds] = await Promise.all([
    // The topic label follows the interface, not the reader's content
    // languages: this heading names the section they are standing in. The
    // articles under it follow the reader.
    getTopics(active.code),
    getArticles({
      languages: readerLanguages(profile?.preferred_languages, active.code),
      topic: topicId,
      cursor,
      pageSize: 24,
    }),
    auth
      ? getSaves(auth).then((page) => new Set(page.data.items.map((item) => item.article.id)))
      : Promise.resolve(new Set<number>()),
  ]);
  const topic = topics.data.find((item) => item.id === topicId);
  if (!topic) notFound();

  return (
    <>
      <div className="page-header">
        <h1>{topic.label}</h1>
      </div>

      {articles.data.items.length === 0 ? (
        <EmptyState
          title={t(active.code, "topics.empty.title", { topic: topic.label })}
          body={t(active.code, "topics.empty.body")}
          action={{
            href: `/${active.code}/topics`,
            label: t(active.code, "topics.allTopics"),
          }}
        />
      ) : (
        <FeedList
          items={articles.data.items.map((article) => ({
            article,
            saved: savedIds.has(article.id),
          }))}
          locale={active.code}
          surface="topic"
          signedIn={Boolean(session)}
          revalidatePath={`/${active.code}/topics/${id}`}
          aboveFold
        />
      )}

      <Pagination
        locale={active.code}
        baseHref={`/${active.code}/topics/${id}`}
        nextCursor={articles.data.next_cursor}
        onLaterPage={Boolean(cursor)}
      />
    </>
  );
}
