import type { Metadata } from "next";
import { Suspense } from "react";
import { notFound } from "next/navigation";

import { EmptyState } from "@/components/EmptyState";
import { FeedList } from "@/components/FeedList";
import { FeedSkeleton } from "@/components/FeedSkeleton";
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

  return (
    <>
      <div className="page-header">
        <h1>{t(active.code, "saved.heading")}</h1>
      </div>
      {/* Suspended rather than left blocking: requireBetaAccess and getSaves
          are both network round trips, and the reader clicked a link to get
          here - the skeleton is what tells them the click worked. */}
      <Suspense key={cursor ?? "start"} fallback={<FeedSkeleton layout="list" secondaries={0} />}>
        <SavedBody locale={active.code} cursor={cursor} />
      </Suspense>
    </>
  );
}

async function SavedBody({
  locale,
  cursor,
}: {
  locale: ReturnType<typeof getLocale>["code"];
  cursor?: string;
}) {
  const access = await requireBetaAccess(locale, `/${locale}/saved`);
  if (!access.ok) return access.element;

  const page = await getSaves(access.auth, cursor);

  return (
    <>
      {page.degraded && (
        <p className="notice" role="status">
          {t(locale, "saved.degraded")}
        </p>
      )}

      {page.data.items.length === 0 ? (
        <EmptyState
          title={t(locale, "saved.empty.title")}
          body={t(locale, "saved.empty.body")}
          action={{ href: `/${locale}`, label: t(locale, "common.backToFeed") }}
        />
      ) : (
        <FeedList
          items={page.data.items.map((item) => ({ article: item.article, saved: true }))}
          locale={locale}
          surface="feed"
          signedIn
          revalidatePath={`/${locale}/saved`}
          layout="list"
        />
      )}

      <Pagination
        locale={locale}
        baseHref={`/${locale}/saved`}
        nextCursor={page.data.next_cursor}
        onLaterPage={Boolean(cursor)}
      />
    </>
  );
}
