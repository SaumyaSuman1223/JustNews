import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { EmptyState } from "@/components/EmptyState";
import { FeedList } from "@/components/FeedList";
import { Pagination } from "@/components/Pagination";
import { getArticles, getEditions } from "@/lib/api";
import { getLocale, isLocaleCode, locales, t } from "@/lib/i18n";
import { getSession } from "@/lib/session";

interface RouteParams {
  locale: string;
  code: string;
}

async function loadEdition(code: string) {
  const editions = await getEditions();
  return editions.data.find((edition) => edition.code === code) ?? null;
}

export async function generateMetadata({
  params,
}: {
  params: Promise<RouteParams>;
}): Promise<Metadata> {
  const { locale, code } = await params;
  const edition = await loadEdition(code);
  return {
    title: edition
      ? edition.name
      : t(isLocaleCode(locale) ? locale : "en", "article.notFound"),
  };
}

export default async function EditionPage({
  params,
  searchParams,
}: {
  params: Promise<RouteParams>;
  searchParams: Promise<{ cursor?: string }>;
}) {
  const { locale, code } = await params;
  if (!isLocaleCode(locale)) notFound();
  const active = getLocale(locale);
  const { cursor } = await searchParams;

  const edition = await loadEdition(code);
  if (!edition) notFound();

  // An edition is a language *and* a place - the language decides what a
  // reader can read, the country decides whose newsroom wrote it.
  const page = await getArticles({
    languages: edition.language,
    country: edition.country ?? undefined,
    cursor,
    pageSize: 24,
  });
  const session = await getSession();

  return (
    <>
      <div className="page-header">
        <h1>{edition.name}</h1>
        {/* The edition's own language, not the interface's. These come apart
            the moment a reader browses a Spanish edition from the English
            site, and the old copy claimed the page was in whichever language
            the chrome happened to be in. */}
        <p>
          {t(active.code, "edition.intro", {
            name: edition.name,
            language:
              locales.find((option) => option.code === edition.language)?.label ??
              edition.language,
          })}
        </p>
      </div>

      {page.degraded && (
        <p className="notice" role="status">
          {t(active.code, "edition.degraded")}
        </p>
      )}

      {page.data.items.length === 0 ? (
        <EmptyState
          title={t(active.code, "edition.empty.title")}
          body={t(active.code, "edition.empty.body")}
          action={{
            href: `/${active.code}/explore`,
            label: t(active.code, "feed.empty.action"),
          }}
        />
      ) : (
        <FeedList
          items={page.data.items.map((article) => ({ article }))}
          locale={active.code}
          surface="topic"
          signedIn={Boolean(session)}
          revalidatePath={`/${active.code}/edition/${edition.code}`}
          aboveFold
        />
      )}

      <Pagination
        locale={active.code}
        baseHref={`/${active.code}/edition/${edition.code}`}
        nextCursor={page.data.next_cursor}
        onLaterPage={Boolean(cursor)}
      />
    </>
  );
}
