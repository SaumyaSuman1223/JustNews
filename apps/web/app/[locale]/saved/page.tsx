import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { ArticleCard } from "@/components/ArticleCard";
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
        <p className="empty">Nothing saved yet. Use &ldquo;Save&rdquo; on any headline.</p>
      ) : (
        <ul className="feed">
          {page.data.items.map((item, index) => (
            <ArticleCard
              key={item.article.id}
              article={item.article}
              locale={active.code}
              surface="feed"
              position={index}
              signedIn
              saved
              revalidatePath={`/${active.code}/saved`}
            />
          ))}
        </ul>
      )}
    </>
  );
}
