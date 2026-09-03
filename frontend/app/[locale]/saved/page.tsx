import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { EmptyState } from "@/components/EmptyState";
import { FeedList } from "@/components/FeedList";
import { Pagination } from "@/components/Pagination";
import { getSaves } from "@/lib/api";
import { getLocale, isLocaleCode, t } from "@/lib/i18n";
import { requireBetaAccess } from "@/lib/guards";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return { title: t(isLocaleCode(locale) ? locale : "en", "saved.heading") };
}

export default async function SavedPage({
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

  const access = await requireBetaAccess(active.code, `/${active.code}/saved`);
  if (!access.ok) return access.element;

  const page = await getSaves(access.auth, cursor);

  return (
    <>
      <div className="page-header">
        <h1>{t(active.code, "saved.heading")}</h1>
      </div>

      {page.degraded && (
        <p className="notice" role="status">
          {t(active.code, "saved.degraded")}
        </p>
      )}

      {page.data.items.length === 0 ? (
        <EmptyState
          title={t(active.code, "saved.empty.title")}
          body={t(active.code, "saved.empty.body")}
          action={{ href: `/${active.code}`, label: t(active.code, "common.backToFeed") }}
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

      <Pagination
        locale={active.code}
        baseHref={`/${active.code}/saved`}
        nextCursor={page.data.next_cursor}
        onLaterPage={Boolean(cursor)}
      />
    </>
  );
}
