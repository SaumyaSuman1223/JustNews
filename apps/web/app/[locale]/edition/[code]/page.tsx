import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { ArticleCard } from "@/components/ArticleCard";
import { getArticles, getEditions } from "@/lib/api";
import { getLocale, isLocaleCode } from "@/lib/i18n";
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
  const { code } = await params;
  const edition = await loadEdition(code);
  return { title: edition ? edition.name : "Not found" };
}

export default async function EditionPage({ params }: { params: Promise<RouteParams> }) {
  const { locale, code } = await params;
  if (!isLocaleCode(locale)) notFound();
  const active = getLocale(locale);

  const edition = await loadEdition(code);
  if (!edition) notFound();

  // An edition is a language *and* a place - the language decides what a
  // reader can read, the country decides whose newsroom wrote it.
  const page = await getArticles({
    languages: edition.language,
    country: edition.country ?? undefined,
    pageSize: 24,
  });
  const session = await getSession();

  return (
    <>
      <div className="page-header">
        <h1>{edition.name}</h1>
        <p>Reported by newsrooms in {edition.name}, in {active.label}.</p>
      </div>

      {page.degraded && (
        <p className="notice" role="status">
          This edition is unavailable right now, so the page may be out of date.
        </p>
      )}

      {page.data.items.length === 0 ? (
        <p className="empty">No headlines from this edition yet.</p>
      ) : (
        <ul className="feed">
          {page.data.items.map((article, index) => (
            <ArticleCard
              key={article.id}
              article={article}
              locale={active.code}
              surface="topic"
              position={index}
              signedIn={Boolean(session)}
              revalidatePath={`/${active.code}/edition/${edition.code}`}
            />
          ))}
        </ul>
      )}
    </>
  );
}
