import type { Metadata } from "next";
import { Suspense } from "react";
import { notFound } from "next/navigation";

import { AddTopicPicker } from "@/components/AddTopicPicker";
import { DeskTiles, type DeskTile } from "@/components/DeskTiles";
import { EmptyState } from "@/components/EmptyState";
import Link from "next/link";

import { getFollows, getTopicOverview, getTopics } from "@/lib/api";
import { getLocale, isLocaleCode, t } from "@/lib/i18n";
import { requireBetaAccess } from "@/lib/guards";

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
      <div className="page-header">
        <h1>{t(active.code, "nav.desk")}</h1>
        <p>{t(active.code, "nav.desk.subtitle")}</p>
      </div>
      <Suspense fallback={<TilesSkeleton />}>
        <DeskBody locale={active.code} />
      </Suspense>
    </>
  );
}

async function DeskBody({
  locale,
}: {
  locale: ReturnType<typeof getLocale>["code"];
}) {
  const access = await requireBetaAccess(locale, `/${locale}/desk`);
  // Audit §28: a gate is a fair authentication state but a poor front door.
  // A visitor who cannot yet sign in should still be able to see what a desk
  // is for - and every topic page behind these links is public, so this shows
  // the real thing rather than a picture of it.
  if (!access.ok) return <DeskPreview locale={locale} gate={access.element} />;

  const [follows, topics] = await Promise.all([
    getFollows(access.auth),
    getTopics(locale),
  ]);
  const byId = new Map(topics.data.map((topic) => [topic.id, topic]));
  const followedIds = new Set(follows.map((f) => f.topic_id));

  const overviews = await Promise.all(
    follows.map((follow) => getTopicOverview(follow.topic_id)),
  );
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

  return (
    <>
      {tiles.length === 0 ? (
        <EmptyState
          title={t(locale, "desk.empty.title")}
          body={t(locale, "desk.empty.body")}
        />
      ) : (
        <DeskTiles
          tiles={tiles}
          locale={locale}
          revalidatePath={`/${locale}/desk`}
        />
      )}

      <AddTopicPicker
        topics={topics.data}
        followedIds={followedIds}
        locale={locale}
        revalidatePath={`/${locale}/desk`}
      />
    </>
  );
}

async function DeskPreview({
  locale,
  gate,
}: {
  locale: ReturnType<typeof getLocale>["code"];
  gate: React.ReactNode;
}) {
  const topics = await getTopics(locale);
  // Real topics, in the reader's interface language, linking to pages that
  // work signed out. Nothing here is a mock-up of a desk someone else has.
  const preview = topics.data.slice(0, 12);

  return (
    <>
      {gate}
      {preview.length > 0 && (
        <section className="desk-preview">
          <h2 className="home-tier">{t(locale, "desk.preview.heading")}</h2>
          <p className="form-note">{t(locale, "desk.preview.body")}</p>
          <ul className="desk-preview__list">
            {preview.map((topic) => (
              <li key={topic.id}>
                <Link
                  className="chip"
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
