import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { notFound } from "next/navigation";

import { DeskRail } from "@/components/DeskRail";
import { EmptyState } from "@/components/EmptyState";
import { FeedList } from "@/components/FeedList";
import { Pagination } from "@/components/Pagination";
import { Perspectives } from "@/components/Perspectives";
import { Timeline } from "@/components/Timeline";
import { TopicDetailSkeleton } from "@/components/TopicDetailSkeleton";
import { TopicStub } from "@/components/TopicStub";
import { TopicTabs, type TopicTab } from "@/components/TopicTabs";
import {
  getArticles,
  getMe,
  getRelatedTopics,
  getSaves,
  getTopicOverview,
  getTopicPerspectives,
  getTopics,
  getTopicStories,
  type Story,
} from "@/lib/api";
import { getBrowsingSessionId } from "@/lib/browsingSession";
import { getLocale, isLocaleCode, readerLanguages, t } from "@/lib/i18n";
import { getSession } from "@/lib/session";

interface RouteParams {
  locale: string;
  id: string;
}

function isTopicTab(value: string | undefined): value is Exclude<TopicTab, "latest"> {
  return value === "timeline" || value === "keyDevelopments" || value === "perspectives" || value === "analysis";
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
    alternates: { canonical: `/${locale}/desk/${encodeURIComponent(topic.id)}` },
  };
}

export default async function TopicDetailPage({
  params,
  searchParams,
}: {
  params: Promise<RouteParams>;
  searchParams: Promise<{ cursor?: string; tab?: string }>;
}) {
  const { locale, id } = await params;
  if (!isLocaleCode(locale)) notFound();
  const active = getLocale(locale);
  const { cursor, tab: tabParam } = await searchParams;
  const tab: TopicTab = isTopicTab(tabParam) ? tabParam : "latest";

  return (
    <Suspense key={`${tab}:${cursor ?? "start"}`} fallback={<TopicDetailSkeleton />}>
      <TopicDetailBody locale={active.code} id={id} cursor={cursor} tab={tab} />
    </Suspense>
  );
}

async function TopicDetailBody({
  locale,
  id,
  cursor,
  tab,
}: {
  locale: ReturnType<typeof getLocale>["code"];
  id: string;
  cursor?: string;
  tab: TopicTab;
}) {
  // The topic id contains a colon (medtop:01000000) - encoded when this page
  // is linked to, and not every router stage decodes it back automatically.
  const topicId = decodeURIComponent(id);

  const session = await getSession();
  const auth = session
    ? { accessToken: session.accessToken, sessionId: await getBrowsingSessionId() }
    : null;
  const profile = auth ? await getMe(auth) : null;

  const [topics, overview, related] = await Promise.all([
    // The topic label follows the interface, not the reader's content
    // languages: this heading names the section they are standing in.
    getTopics(locale),
    getTopicOverview(topicId),
    getRelatedTopics(topicId, locale),
  ]);
  const topic = topics.data.find((item) => item.id === topicId);
  if (!topic) notFound();

  const basePath = `/${locale}/desk/${id}`;

  return (
    <>
      <div className="page-header">
        <h1>{topic.label}</h1>
      </div>

      <TopicTabs locale={locale} active={tab} basePath={basePath} />

      <div className="desk-layout">
        <div className="desk-layout__main">
          <TabBody
            tab={tab}
            locale={locale}
            topicId={topicId}
            topicLabel={topic.label}
            basePath={basePath}
            cursor={cursor}
            auth={auth}
            languages={readerLanguages(profile?.preferred_languages, locale)}
            signedIn={Boolean(session)}
          />
        </div>
        <DeskRail
          overview={overview.degraded ? null : overview.data}
          related={related.data}
          locale={locale}
        />
      </div>
    </>
  );
}

async function TabBody({
  tab,
  locale,
  topicId,
  topicLabel,
  basePath,
  cursor,
  auth,
  languages,
  signedIn,
}: {
  tab: TopicTab;
  locale: ReturnType<typeof getLocale>["code"];
  topicId: string;
  topicLabel: string;
  basePath: string;
  cursor?: string;
  auth: { accessToken: string; sessionId: string | null } | null;
  languages: string;
  signedIn: boolean;
}) {
  if (tab === "timeline" || tab === "keyDevelopments") {
    const stories = await getTopicStories(topicId);
    const items: Story[] = stories.degraded ? [] : stories.data;
    if (tab === "keyDevelopments") {
      // Same fetch as Timeline, re-sorted: breadth of coverage rather than
      // when it broke - "key" as in widely reported, not as in newest.
      const byBreadth = items
        .slice()
        .sort((a, b) => b.source_count - a.source_count || b.article_count - a.article_count)
        .slice(0, 5);
      return byBreadth.length === 0 ? (
        <p className="notice">{t(locale, "desk.keyDevelopments.empty")}</p>
      ) : (
        <ol className="trending__list">
          {byBreadth.map((story) => (
            <li key={story.id} className="trending__item">
              <Link className="trending__link" href={`/${locale}/story/${story.id}`}>
                {story.title}
              </Link>
              <p className="trending__meta">
                {t(locale, "desk.timeline.coverage", {
                  sources: story.source_count,
                  languages: story.language_count,
                })}
              </p>
            </li>
          ))}
        </ol>
      );
    }
    return (
      <Timeline
        stories={items}
        locale={locale}
        topicHref={(storyId) => `/${locale}/story/${storyId}`}
      />
    );
  }

  if (tab === "perspectives") {
    const groups = await getTopicPerspectives(topicId);
    return <Perspectives groups={groups.degraded ? [] : groups.data} locale={locale} />;
  }

  if (tab === "analysis") {
    return (
      <TopicStub
        title={t(locale, "desk.stub.analysis.title")}
        body={t(locale, "desk.stub.analysis.body")}
      />
    );
  }

  // "latest" - the topic's own ranked feed of articles, same as before.
  const [articles, savedIds] = await Promise.all([
    getArticles({ languages, topic: topicId, cursor, pageSize: 24 }),
    auth
      ? getSaves(auth).then((page) => new Set(page.data.items.map((item) => item.article.id)))
      : Promise.resolve(new Set<number>()),
  ]);

  if (articles.data.items.length === 0) {
    return (
      <EmptyState
        title={t(locale, "topics.empty.title", { topic: topicLabel })}
        body={t(locale, "topics.empty.body")}
        action={{ href: `/${locale}/desk`, label: t(locale, "nav.desk") }}
      />
    );
  }

  return (
    <>
      <FeedList
        items={articles.data.items.map((article) => ({
          article,
          saved: savedIds.has(article.id),
        }))}
        locale={locale}
        surface="topic"
        signedIn={signedIn}
        revalidatePath={basePath}
        aboveFold
      />
      <Pagination
        locale={locale}
        baseHref={basePath}
        nextCursor={articles.data.next_cursor}
        onLaterPage={Boolean(cursor)}
      />
    </>
  );
}
