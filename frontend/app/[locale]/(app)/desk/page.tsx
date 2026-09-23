import type { Metadata } from "next";
import { Suspense } from "react";
import { notFound } from "next/navigation";

import { AddTopicPicker } from "@/components/AddTopicPicker";
import { DeskTiles, type DeskTile } from "@/components/DeskTiles";
import { EmptyState } from "@/components/EmptyState";
import { Understand } from "@/components/Understand";
import Link from "next/link";

import { WhatChanged, type TopicChange } from "@/components/WhatChanged";

import {
  getArticles,
  getFollowedStories,
  getFollows,
  getTopicOverview,
  getTopicPerspectives,
  getTopicStories,
  getTopics,
  type StoryFollow,
} from "@/lib/api";
import { withCuratedLabels } from "@/lib/curatedTopics";
import { getLocale, isLocaleCode, t, tPlural } from "@/lib/i18n";
import { requireBetaAccess } from "@/lib/guards";

/** How many followed topics "What changed" reports on. A cap, not a
 * preference: each one is a separate request. */
const WHAT_CHANGED_TOPICS = 6;

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return { title: t(isLocaleCode(locale) ? locale : "en", "nav.desk") };
}

function TilesSkeleton() {
  return (
    <ul className="desk-tiles" aria-hidden="true">
      {Array.from({ length: 4 }, (_, index) => (
        <li className="desk-tile" key={index}>
          <div className="skeleton skeleton--chip" />
        </li>
      ))}
    </ul>
  );
}

export default async function DeskPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  if (!isLocaleCode(locale)) notFound();
  const active = getLocale(locale);

  return (
    <>
      {/* §24's header, and §23's answer to "the current My Desk is
          essentially a sign-in gate": the page says what it is for before it
          asks for anything. */}
      <div className="page-header">
        <h1>{t(active.code, "nav.desk")}</h1>
        <p>{t(active.code, "desk.subtitle")}</p>
      </div>
      <Suspense fallback={<TilesSkeleton />}>
        <DeskBody locale={active.code} />
      </Suspense>
    </>
  );
}

/**
 * The most recent development in each topic, paired with its label.
 *
 * "Most recent" is `last_seen_at` - when coverage was last added to the
 * cluster - tie-broken by how many publishers are carrying it. Both are real
 * columns on the cluster; this decides nothing about importance on its own.
 */
function latestChanges(
  topics: ({ id: string; label: string } | undefined)[],
  storyLists: Awaited<ReturnType<typeof getTopicStories>>[],
): TopicChange[] {
  return topics
    .map((topic, index) => {
      const stories = storyLists[index];
      if (!topic || !stories || stories.degraded) return null;
      const latest = stories.data
        .slice()
        .sort(
          (a, b) =>
            Date.parse(b.last_seen_at) - Date.parse(a.last_seen_at) ||
            b.source_count - a.source_count,
        )[0];
      return latest ? { topicId: topic.id, label: topic.label, story: latest } : null;
    })
    .filter((change): change is TopicChange => change !== null);
}

async function DeskBody({
  locale,
}: {
  locale: ReturnType<typeof getLocale>["code"];
}) {
  const access = await requireBetaAccess(locale, `/${locale}/desk`, {
    title: t(locale, "desk.gate.title"),
    body: t(locale, "desk.gate.body"),
    embedded: true,
  });
  // Audit §28: a gate is a fair authentication state but a poor front door.
  // A visitor who cannot yet sign in should still be able to see what a desk
  // is for - and every topic page behind these links is public, so this shows
  // the real thing rather than a picture of it.
  if (!access.ok) return <DeskPreview locale={locale} gate={access.element} />;

  const [follows, topicsRaw, followedStories] = await Promise.all([
    getFollows(access.auth),
    getTopics(locale),
    getFollowedStories(access.auth),
  ]);
  // §24's curated layer, applied once here so every reader below - tiles,
  // the add-topic picker, "what changed" headings - sees the editorial
  // label without repeating the lookup at each call site.
  const topics = { ...topicsRaw, data: withCuratedLabels(topicsRaw.data, locale) };
  const byId = new Map(topics.data.map((topic) => [topic.id, topic]));
  const followedIds = new Set(follows.map((f) => f.topic_id));

  // One overview per followed topic, as before, plus one story list for the
  // first few - "what changed" is a per-topic question and there is no batch
  // endpoint for it. Capped rather than unbounded: a reader following thirty
  // topics should not make this page thirty round trips deep.
  const changeTopics = follows.slice(0, WHAT_CHANGED_TOPICS);
  const [overviews, storyLists] = await Promise.all([
    Promise.all(follows.map((follow) => getTopicOverview(follow.topic_id))),
    Promise.all(changeTopics.map((follow) => getTopicStories(follow.topic_id, 10))),
  ]);

  const tiles: DeskTile[] = follows
    .map((follow, index) => {
      const topic = byId.get(follow.topic_id);
      if (!topic) return null;
      const overview = overviews[index];
      return {
        topicId: follow.topic_id,
        label: topic.label,
        articleCount:
          overview?.degraded || !overview?.data ? 0 : overview.data.articles,
      };
    })
    .filter((tile): tile is DeskTile => tile !== null);

  const changes = latestChanges(
    changeTopics.map((follow) => byId.get(follow.topic_id)),
    storyLists,
  );

  if (tiles.length === 0) {
    return (
      <>
        <FollowedStories stories={followedStories} locale={locale} />
        <EmptyState
          title={t(locale, "desk.empty.title")}
          body={t(locale, "desk.empty.body")}
        />
        <AddTopicPicker
          topics={topics.data}
          followedIds={followedIds}
          locale={locale}
          revalidatePath={`/${locale}/desk`}
        />
      </>
    );
  }

  return (
    <>
      {/* Followed stories first: a story the reader chose to track, with a
          count of what arrived since, is the most specific thing this page
          can tell them. */}
      <FollowedStories stories={followedStories} locale={locale} />
      {/* What changed comes first. The topics themselves are the workspace's
          furniture - useful, and not the thing a reader opened the page to
          find out (§25, §27). */}
      <section className="desk-section">
        <h2 className="home-tier">{t(locale, "desk.whatChanged")}</h2>
        <p className="desk-section__note">{t(locale, "desk.whatChanged.note")}</p>
        <WhatChanged changes={changes} locale={locale} />
      </section>

      <section className="desk-section">
        <h2 className="home-tier">{t(locale, "desk.yourTopics")}</h2>
        <DeskTiles
          tiles={tiles}
          locale={locale}
          revalidatePath={`/${locale}/desk`}
        />
        <AddTopicPicker
          topics={topics.data}
          followedIds={followedIds}
          locale={locale}
          revalidatePath={`/${locale}/desk`}
        />
      </section>
    </>
  );
}

/**
 * The stories this reader follows (fifth pass F2), unseen reports first -
 * each with how many reports arrived since they last opened it. Renders
 * nothing until they follow one: an empty "stories you follow" box on every
 * desk would be furniture asking for attention.
 */
function FollowedStories({
  stories,
  locale,
}: {
  stories: StoryFollow[];
  locale: ReturnType<typeof getLocale>["code"];
}) {
  if (stories.length === 0) return null;
  return (
    <section className="desk-section">
      <h2 className="home-tier">{t(locale, "desk.followedStories")}</h2>
      <p className="desk-section__note">{t(locale, "desk.followedStories.note")}</p>
      <ul className="followed-stories">
        {stories.map((story) => (
          <li key={story.story_id}>
            <Link href={`/${locale}/story/${story.story_id}`}>{story.title}</Link>
            <span
              className={
                story.new_reports > 0
                  ? "followed-stories__count followed-stories__count--new"
                  : "followed-stories__count"
              }
            >
              {story.new_reports > 0
                ? tPlural(locale, "desk.followedStories.new", story.new_reports)
                : t(locale, "desk.followedStories.upToDate")}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}

async function DeskPreview({
  locale,
  gate,
}: {
  locale: ReturnType<typeof getLocale>["code"];
  gate: React.ReactNode;
}) {
  const topicsRaw = await getTopics(locale);
  // Real topics, in the reader's interface language and §24's curated
  // labels, linking to pages that work signed out. Nothing here is a
  // mock-up of a desk someone else has.
  const preview = withCuratedLabels(topicsRaw.data, locale).slice(0, 12);

  // §23: "the current My Desk is essentially a sign-in gate. That is not
  // enough." A visitor who cannot sign in yet still gets the page's actual
  // answer - what has moved in these topics - because story clusters are a
  // public read. This is the same section a signed-in reader gets, over
  // topics nobody has chosen yet rather than over theirs.
  const changeTopics = preview.slice(0, WHAT_CHANGED_TOPICS);
  const storyLists = await Promise.all(
    changeTopics.map((topic) => getTopicStories(topic.id, 10)),
  );
  const changes = latestChanges(changeTopics, storyLists);

  // Fourth-pass §20: the page should demonstrate the value before it asks
  // for an account, not describe it. One real topic, rendered with the same
  // `Understand` module a signed-in reader's own topic page uses - not a
  // screenshot of one, the thing itself, working signed out.
  //
  // Fifth-pass §2.1: "the first topic with any story" picked Climate, whose
  // stories were a podcast and a documentary at one source each - under a
  // pitch promising "compare who is covering it". The example is now the
  // topic with the broadest real coverage: most outlets, then most articles,
  // read from each topic's own overview counts.
  const overviews = await Promise.all(preview.map((topic) => getTopicOverview(topic.id)));
  const breadth = (index: number): [number, number] => {
    const overview = overviews[index];
    const data = overview && !overview.degraded ? overview.data : null;
    return data ? [data.sources, data.articles] : [0, 0];
  };
  let exampleIndex = -1;
  preview.forEach((_, index) => {
    const [sources, articles] = breadth(index);
    if (articles === 0) return;
    const [bestSources, bestArticles] = exampleIndex >= 0 ? breadth(exampleIndex) : [-1, -1];
    if (sources > bestSources || (sources === bestSources && articles > bestArticles)) {
      exampleIndex = index;
    }
  });
  const example = exampleIndex >= 0 ? (preview[exampleIndex] ?? null) : null;
  const [exampleStories, examplePerspectives, exampleLatest] = example
    ? await Promise.all([
        getTopicStories(example.id),
        getTopicPerspectives(example.id),
        getArticles({ languages: locale, topic: example.id, pageSize: 24 }),
      ])
    : [null, null, null];
  // The example already shows its own topic in full; "what changed" below
  // covers the others, so nothing on the page is printed twice.
  const shownStoryIds = new Set(
    exampleStories && !exampleStories.degraded ? exampleStories.data.map((story) => story.id) : [],
  );
  // A showcase for someone deciding whether to sign up features only stories
  // more than one outlet is carrying - the same bar Understand sets for a
  // "development". A signed-in reader's own desk still reports every change
  // in the topics they chose.
  const otherChanges = changes.filter(
    (change) =>
      change.topicId !== example?.id &&
      !shownStoryIds.has(change.story.id) &&
      change.story.source_count > 1,
  );

  return (
    <>
      <section className="desk-pitch">
        <h2 className="home-tier">{t(locale, "desk.pitch.heading")}</h2>
        <ul className="desk-pitch__list">
          <li>{t(locale, "desk.pitch.follow")}</li>
          <li>{t(locale, "desk.pitch.changed")}</li>
          <li>{t(locale, "desk.pitch.perspectives")}</li>
          <li>{t(locale, "desk.pitch.track")}</li>
        </ul>
      </section>

      {example && exampleStories && examplePerspectives && exampleLatest && (
        <section className="desk-example">
          <p className="desk-section__note">{t(locale, "desk.example.note")}</p>
          <Understand
            topicLabel={example.label}
            stories={exampleStories.degraded ? [] : exampleStories.data}
            perspectives={examplePerspectives.degraded ? [] : examplePerspectives.data}
            latest={exampleLatest.degraded ? [] : exampleLatest.data.items}
            locale={locale}
            storyHref={(storyId) => `/${locale}/story/${storyId}`}
          />
        </section>
      )}

      <section className="desk-section desk-section--gate">
        {gate}
      </section>

      {otherChanges.length > 0 && (
        <section className="desk-section">
          <h2 className="home-tier">{t(locale, "desk.whatChanged")}</h2>
          <p className="desk-section__note">
            {t(locale, "desk.whatChanged.previewNote")}
          </p>
          <WhatChanged changes={otherChanges} locale={locale} />
        </section>
      )}
      {preview.length > 0 && (
        <section className="desk-preview">
          <h2 className="home-tier">{t(locale, "desk.preview.heading")}</h2>
          <p className="form-note">{t(locale, "desk.preview.body")}</p>
          <ul className="desk-preview__list topic-picker">
            {preview.map((topic) => (
              <li key={topic.id}>
                <Link
                  className="topic-chip"
                  href={`/${locale}/desk/${encodeURIComponent(topic.id)}`}
                >
                  {topic.label}
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}
    </>
  );
}
