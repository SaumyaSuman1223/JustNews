import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { ArticleCard } from "@/components/ArticleCard";
import { SignInRequired } from "@/components/SignInRequired";
import { getHistory, getSaves } from "@/lib/api";
import { getBrowsingSessionId } from "@/lib/browsingSession";
import { formatRelativeTime, getLocale, isLocaleCode } from "@/lib/i18n";
import { getSession } from "@/lib/session";

export const metadata: Metadata = { title: "History" };

export default async function HistoryPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  if (!isLocaleCode(locale)) notFound();
  const active = getLocale(locale);
  const session = await getSession();

  if (!session) return <SignInRequired locale={active.code} path={`/${active.code}/history`} />;

  const auth = { accessToken: session.accessToken, sessionId: await getBrowsingSessionId() };
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
        <p className="empty">Nothing here yet - articles you open will show up here.</p>
      ) : (
        <ul className="feed">
          {page.data.items.map((item, index) => (
            <ArticleCard
              key={`${item.article.id}-${item.viewed_at}`}
              article={item.article}
              locale={active.code}
              surface="feed"
              position={index}
              signedIn
              saved={savedIds.has(item.article.id)}
              revalidatePath={`/${active.code}/history`}
              footnote={`Viewed ${formatRelativeTime(item.viewed_at, active.code)}`}
            />
          ))}
        </ul>
      )}
    </>
  );
}
