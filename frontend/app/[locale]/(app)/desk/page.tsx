import type { Metadata } from "next";
import { Suspense } from "react";
import { notFound } from "next/navigation";

import { AddTopicPicker } from "@/components/AddTopicPicker";
import { DeskTiles, type DeskTile } from "@/components/DeskTiles";
import { EmptyState } from "@/components/EmptyState";
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

export default async function DeskPage({ params }: { params: Promise<{ locale: string }> }) {
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

async function DeskBody({ locale }: { locale: ReturnType<typeof getLocale>["code"] }) {
  const access = await requireBetaAccess(locale, `/${locale}/desk`);
  if (!access.ok) return access.element;

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
        articleCount: overview?.degraded || !overview?.data ? 0 : overview.data.articles,
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
        <DeskTiles tiles={tiles} locale={locale} revalidatePath={`/${locale}/desk`} />
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
