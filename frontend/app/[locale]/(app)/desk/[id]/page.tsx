import type { Metadata } from "next";
import { Suspense } from "react";
import { notFound } from "next/navigation";

import { DeskRail } from "@/components/DeskRail";
import { EmptyState } from "@/components/EmptyState";
import { FeedList } from "@/components/FeedList";
import { Pagination } from "@/components/Pagination";
import { TopicDetailSkeleton } from "@/components/TopicDetailSkeleton";
import { TopicStub } from "@/components/TopicStub";
import { TopicTabs, type TopicTab } from "@/components/TopicTabs";
import { Understand } from "@/components/Understand";
import {
  getArticles,
  getMe,
  getRelatedTopics,
  getSaves,
  getTopicOverview,
  getTopicPerspectives,
  getTopics,
  getTopicStories,
} from "@/lib/api";
import { getBrowsingSessionId } from "@/lib/browsingSession";
import { getLocale, isLocaleCode, readerLanguages, t } from "@/lib/i18n";
import { getSession } from "@/lib/session";

interface RouteParams {
  locale: string;
  id: string;
}

function isTopicTab(value: string | undefined): value is Exclude<TopicTab, "understand"> {
  return value === "latest" || value === "analysis";
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
  const tab: TopicTab = isTopicTab(tabParam) ? tabParam : "understand";

  return (
    // Keyed by cursor alone, not tab: a tab switch must stay the same
    // Suspense boundary so React's transition keeps the outgoing tab's
    // content on screen (see TopicTabs) instead of discarding it for the
    // fallback skeleton. A cursor change (paging within a tab) still gets a
    // fresh boundary, same as before.
    <Suspense key={cursor ?? "start"} fallback={<TopicDetailSkeleton />}>
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

      <TopicTabs locale={locale} active={tab} basePath={basePath}>
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
      </TopicTabs>
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
  if (tab === "understand") {
    // Both reads in parallel, and the story list serves two of the three
    // modules - see Understand, which sorts the same array two ways.
    const [stories, groups] = await Promise.all([
      getTopicStories(topicId),
      getTopicPerspectives(topicId),
    ]);
    return (
      <Understand
        topicLabel={topicLabel}
        stories={stories.degraded ? [] : stories.data}
        perspectives={groups.degraded ? [] : groups.data}
        locale={locale}
        storyHref={(storyId) => `/${locale}/story/${storyId}`}
      />
    );
  }

  if (tab === "analysis") {
    return (
      <TopicStub
        title={t(locale, "desk.stub.analysis.title")}
        body={t(locale, "desk.stub.analysis.body")}
      />
    );
  }

  // "latest" - the topic's own ranked feed of articles, unchanged.
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
