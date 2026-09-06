import { notFound } from "next/navigation";

import { FeedList, type FeedItem } from "@/components/FeedList";
import { getArticles } from "@/lib/api";
import { getLocale, isLocaleCode } from "@/lib/i18n";
import type { RankReason } from "@/lib/rankReason";

/**
 * Preview only, for the "why am I seeing this?" disclosure design-system.md
 * calls non-negotiable. There is no real data source yet: `FeedItemOut`
 * carries no reason field, and Stage 5 - the ranker that would compute one -
 * has not started. This route exists so the component is reviewable against
 * real article content without any real beta reader ever being given a
 * reason the product cannot actually back up yet.
 *
 * Confirmed with the user: dev-only, blocked in every deployed environment,
 * not just unlinked from navigation. `NODE_ENV === "production"` covers a
 * `next build` for staging and for production alike - both are reachable by
 * URL, and "no real reader reaches it" has to mean neither serves this.
 */
const MOCK_REASONS: RankReason[] = [
  { kind: "followed_topic", topic: "Technology" },
  { kind: "followed_source", source: "Example Wire" },
  { kind: "trending" },
  { kind: "exploration" },
];

export default async function WhyAmISeeingThisPreview({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  if (process.env.NODE_ENV === "production") notFound();

  const { locale } = await params;
  if (!isLocaleCode(locale)) notFound();
  const active = getLocale(locale);

  const page = await getArticles({ languages: active.code, pageSize: 8 });

  const items: FeedItem[] = page.data.items.map((article, index) => ({
    article,
    why: MOCK_REASONS[index % MOCK_REASONS.length],
  }));

  return (
    <div className="narrow">
      <div className="page-header">
        <h1>“Why am I seeing this?” — preview</h1>
        <p>
          Real articles, mock reasons cycling through the four kinds in <code>lib/rankReason.ts</code>.
          Not reachable in a deployed environment - see the block at the top of this file and
          PRODUCT.md&rsquo;s Operating Context.
        </p>
      </div>
      {items.length === 0 ? (
        <p>No articles available in this language to preview against right now.</p>
      ) : (
        <FeedList
          items={items}
          locale={active.code}
          surface="feed"
          signedIn={false}
          revalidatePath={`/${active.code}/dev/why`}
          layout="list"
        />
      )}
    </div>
  );
}
