import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { EmptyState } from "@/components/EmptyState";
import { FeedList } from "@/components/FeedList";
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

export default async function HistoryPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  if (!isLocaleCode(locale)) notFound();
  const active = getLocale(locale);

  const access = await requireBetaAccess(active.code, `/${active.code}/history`);
  if (!access.ok) return access.element;

  const { auth } = access;
  const [page, saves] = await Promise.all([getHistory(auth), getSaves(auth)]);
  const savedIds = new Set(saves.data.items.map((item) => item.article.id));

  return (
    <>
      <div className="page-header">
        <h1>{t(active.code, "history.heading")}</h1>
        <p>{t(active.code, "history.intro")}</p>
      </div>

      {page.degraded && (
        <p className="notice" role="status">
          {t(active.code, "history.degraded")}
        </p>
      )}

      {page.data.items.length === 0 ? (
        <EmptyState
          title={t(active.code, "history.empty.title")}
          body={t(active.code, "history.empty.body")}
          action={{ href: `/${active.code}`, label: t(active.code, "common.backToFeed") }}
        />
      ) : (
        <FeedList
          items={page.data.items.map((item) => ({
            key: `${item.article.id}-${item.viewed_at}`,
            article: item.article,
            saved: savedIds.has(item.article.id),
            footnote: t(active.code, "history.viewed", {
              time: formatRelativeTime(item.viewed_at, active.code),
            }),
          }))}
          locale={active.code}
          surface="feed"
          signedIn
          revalidatePath={`/${active.code}/history`}
          layout="list"
        />
      )}
    </>
  );
}
