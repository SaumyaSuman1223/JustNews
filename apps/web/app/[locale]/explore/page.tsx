import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { ArticleCard } from "@/components/ArticleCard";
import { BlindspotRail } from "@/components/BlindspotRail";
import { getBlindspots, getExplore, getSaves } from "@/lib/api";
import { getBrowsingSessionId } from "@/lib/browsingSession";
import { getLocale, isLocaleCode } from "@/lib/i18n";
import { getSession } from "@/lib/session";

export const metadata: Metadata = { title: "Explore" };

// Every request logs the impressions it served, so this page cannot be
// statically rendered or shared from a cache - two readers must not be
// attributed the same impression rows.
export const dynamic = "force-dynamic";

export default async function ExplorePage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  if (!isLocaleCode(locale)) notFound();
  const active = getLocale(locale);

  // Deliberately no beta gate and no sign-in requirement: explore is the
  // surface a reader sees *before* they have either.
  const session = await getSession();
  const auth = session
    ? { accessToken: session.accessToken, sessionId: await getBrowsingSessionId() }
    : null;

  const [page, blindspots, savedIds] = await Promise.all([
    getExplore(auth, { locale: active.code, languages: active.code, pageSize: 24 }),
    getBlindspots(active.code),
    auth
      ? getSaves(auth).then((saves) => new Set(saves.data.items.map((item) => item.article.id)))
      : Promise.resolve(new Set<number>()),
  ]);

  return (
    <>
      <div className="page-header">
        <h1>Explore</h1>
        <p>
          The latest across every source we follow, ranked by recency and spread across topics -
          the same for everyone, whether or not you are signed in.
        </p>
      </div>

      {page.degraded && (
        <p className="notice" role="status">
          Live headlines are unavailable right now, so this page may be out of date.
        </p>
      )}

      <BlindspotRail blindspots={blindspots.data} locale={active.code} />

      {page.data.items.length === 0 ? (
        <p className="empty">Nothing to explore in {active.label} just yet. Try another language.</p>
      ) : (
        <ul className="feed">
          {page.data.items.map((item, index) => (
            <ArticleCard
              key={item.article.id}
              article={item.article}
              impressionId={item.impression_id}
              locale={active.code}
              surface="explore"
              position={index}
              signedIn={Boolean(auth)}
              saved={savedIds.has(item.article.id)}
              revalidatePath={`/${active.code}/explore`}
            />
          ))}
        </ul>
      )}
    </>
  );
}
