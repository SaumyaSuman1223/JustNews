import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { ArticleCard } from "@/components/ArticleCard";
import { getArticles, getSaves, getTopics } from "@/lib/api";
import { getBrowsingSessionId } from "@/lib/browsingSession";
import { getLocale, isLocaleCode } from "@/lib/i18n";
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
  if (!topic) return { title: "Topic" };
  return {
    title: topic.label,
    alternates: { canonical: `/${locale}/topics/${encodeURIComponent(topic.id)}` },
  };
}

export default async function TopicDetailPage({ params }: { params: Promise<RouteParams> }) {
  const { locale, id } = await params;
  if (!isLocaleCode(locale)) notFound();
  const active = getLocale(locale);
  // The topic id contains a colon (medtop:01000000) - encoded when this page
  // is linked to, and not every router stage decodes it back automatically.
  const topicId = decodeURIComponent(id);

  const [topics, articles, session] = await Promise.all([
    getTopics(active.code),
    getArticles({ languages: active.code, topic: topicId, pageSize: 24 }),
    getSession(),
  ]);
  const topic = topics.data.find((item) => item.id === topicId);
  if (!topic) notFound();

  const savedIds = session
    ? await getSaves({
        accessToken: session.accessToken,
        sessionId: await getBrowsingSessionId(),
      }).then((page) => new Set(page.data.items.map((item) => item.article.id)))
    : new Set<number>();

  return (
    <>
      <div className="page-header">
        <h1>{topic.label}</h1>
      </div>

      {articles.data.items.length === 0 ? (
        <p className="empty">
          Nothing tagged {topic.label} in {active.label} yet.
        </p>
      ) : (
        <ul className="feed">
          {articles.data.items.map((article, index) => (
            <ArticleCard
              key={article.id}
              article={article}
              locale={active.code}
              surface="topic"
              position={index}
              signedIn={Boolean(session)}
              saved={savedIds.has(article.id)}
              revalidatePath={`/${active.code}/topics/${id}`}
            />
          ))}
        </ul>
      )}
    </>
  );
}
