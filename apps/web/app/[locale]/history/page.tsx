import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { EmptyState } from "@/components/EmptyState";
import { FeedList } from "@/components/FeedList";
import { getHistory, getSaves } from "@/lib/api";
import { formatRelativeTime, getLocale, isLocaleCode } from "@/lib/i18n";
import { requireBetaAccess } from "@/lib/guards";

export const metadata: Metadata = { title: "History" };

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
        <h1>History</h1>
        <p>Articles you have opened, most recent first.</p>
      </div>

      {page.degraded && (
        <p className="notice" role="status">
          History is unavailable right now.
        </p>
      )}

      {page.data.items.length === 0 ? (
        <EmptyState
          title="No reading history yet"
          body="Articles you open appear here, most recent first. Only you can see this."
          action={{ href: `/${active.code}`, label: "Back to the feed" }}
        />
      ) : (
        <FeedList
          items={page.data.items.map((item) => ({
            key: `${item.article.id}-${item.viewed_at}`,
            article: item.article,
            saved: savedIds.has(item.article.id),
            footnote: `Viewed ${formatRelativeTime(item.viewed_at, active.code)}`,
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
