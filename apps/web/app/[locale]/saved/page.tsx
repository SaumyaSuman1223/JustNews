import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { ArticleCard } from "@/components/ArticleCard";
import { SignInRequired } from "@/components/SignInRequired";
import { getSaves } from "@/lib/api";
import { getBrowsingSessionId } from "@/lib/browsingSession";
import { getLocale, isLocaleCode } from "@/lib/i18n";
import { getSession } from "@/lib/session";

export const metadata: Metadata = { title: "Saved" };

export default async function SavedPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  if (!isLocaleCode(locale)) notFound();
  const active = getLocale(locale);
  const session = await getSession();

  if (!session) return <SignInRequired locale={active.code} path={`/${active.code}/saved`} />;

  const page = await getSaves({
    accessToken: session.accessToken,
    sessionId: await getBrowsingSessionId(),
  });

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
