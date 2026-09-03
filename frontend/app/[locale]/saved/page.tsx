import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { EmptyState } from "@/components/EmptyState";
import { FeedList } from "@/components/FeedList";
import { getSaves } from "@/lib/api";
import { getLocale, isLocaleCode } from "@/lib/i18n";
import { requireBetaAccess } from "@/lib/guards";

export const metadata: Metadata = { title: "Saved" };

export default async function SavedPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  if (!isLocaleCode(locale)) notFound();
  const active = getLocale(locale);

  const access = await requireBetaAccess(active.code, `/${active.code}/saved`);
  if (!access.ok) return access.element;

  const page = await getSaves(access.auth);

  return (
    <>
      <div className="page-header">
        <h1>Saved</h1>
      </div>

      {page.degraded && (
        <p className="notice" role="status">
          Saved articles are unavailable right now.
        </p>
      )}

      {page.data.items.length === 0 ? (
        <EmptyState
          title="Nothing saved yet"
          body={"Every headline has a Save button. Saved stories stay here, and they keep working after the article scrolls off the feed."}
          action={{ href: `/${active.code}`, label: "Back to the feed" }}
        />
      ) : (
        <FeedList
          items={page.data.items.map((item) => ({ article: item.article, saved: true }))}
          locale={active.code}
          surface="feed"
          signedIn
          revalidatePath={`/${active.code}/saved`}
          layout="list"
        />
      )}
    </>
  );
}
