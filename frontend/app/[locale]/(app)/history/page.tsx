import type { Metadata } from "next";
import { Suspense } from "react";
import { notFound } from "next/navigation";

import { EmptyState } from "@/components/EmptyState";
import { FeedList } from "@/components/FeedList";
import { FeedSkeleton } from "@/components/FeedSkeleton";
import { Pagination } from "@/components/Pagination";
import { getHistory, getSaves } from "@/lib/api";
import { formatRelativeTime, getLocale, isLocaleCode, t } from "@/lib/i18n";
import { requireBetaAccess } from "@/lib/guards";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return { title: t(isLocaleCode(locale) ? locale : "en", "history.heading") };
}

export default async function HistoryPage({
  params,
  searchParams,
}: {
  params: Promise<{ locale: string }>;
  searchParams: Promise<{ cursor?: string }>;
}) {
  const { locale } = await params;
  if (!isLocaleCode(locale)) notFound();
  const active = getLocale(locale);
  const { cursor } = await searchParams;

  return (
    <>
      <div className="page-header">
        <h1>{t(active.code, "history.heading")}</h1>
        <p>{t(active.code, "history.intro")}</p>
      </div>
      <Suspense key={cursor ?? "start"} fallback={<FeedSkeleton layout="list" secondaries={0} />}>
        <HistoryBody locale={active.code} cursor={cursor} />
      </Suspense>
    </>
  );
}

async function HistoryBody({
  locale,
  cursor,
}: {
  locale: ReturnType<typeof getLocale>["code"];
  cursor?: string;
}) {
  const access = await requireBetaAccess(locale, `/${locale}/history`);
  if (!access.ok) return access.element;

  const { auth } = access;
  // The cursor paginates history; saves stays on its first page, which is
  // only used to mark which rows are already saved.
  const [page, saves] = await Promise.all([getHistory(auth, cursor), getSaves(auth)]);
  const savedIds = new Set(saves.data.items.map((item) => item.article.id));

  return (
    <>
      {page.degraded && (
        <p className="notice" role="status">
          {t(locale, "history.degraded")}
        </p>
      )}

      {page.data.items.length === 0 ? (
        <EmptyState
          title={t(locale, "history.empty.title")}
          body={t(locale, "history.empty.body")}
          action={{ href: `/${locale}`, label: t(locale, "common.backToFeed") }}
        />
      ) : (
        <FeedList
          items={page.data.items.map((item) => ({
            key: `${item.article.id}-${item.viewed_at}`,
            article: item.article,
            saved: savedIds.has(item.article.id),
            footnote: t(locale, "history.viewed", {
              time: formatRelativeTime(item.viewed_at, locale),
            }),
          }))}
          locale={locale}
          surface="feed"
          signedIn
          revalidatePath={`/${locale}/history`}
          layout="list"
        />
      )}

      <Pagination
        locale={locale}
        baseHref={`/${locale}/history`}
        nextCursor={page.data.next_cursor}
        onLaterPage={Boolean(cursor)}
      />
    </>
  );
}
