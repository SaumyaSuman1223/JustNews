import { ArticleCard, type CardVariant } from "@/components/ArticleCard";
import type { Article } from "@/lib/api";
import type { LocaleCode } from "@/lib/i18n";
import type { RankReason } from "@/lib/rankReason";

export interface FeedItem {
  article: Article;
  /** Present only where an impression was actually logged (ranked surfaces). */
  impressionId?: number | null;
  saved?: boolean;
  footnote?: string;
  /** See ArticleCard's `why` - undefined on every real feed today. */
  why?: RankReason;
  /** Overrides the article id as the React key, for lists that can repeat an
   * article - history being the one that does. */
  key?: string;
}

export interface FeedListProps {
  items: FeedItem[];
  locale: LocaleCode;
  surface: "feed" | "explore" | "search" | "topic" | "onboarding";
  signedIn: boolean;
  revalidatePath: string;
  /**
   * `edited` gives the run a front-page shape: one lead, a band of secondaries,
   * then list rows. `list` keeps every row the same weight, which is right for
   * a set the reader assembled themselves (saved, history) - promoting one of
   * those to a lead would be the page inventing an editorial judgement it has
   * no basis for.
   */
  layout?: "edited" | "list";
  /** Set on the first screenful of the page, so the lead image preloads. */
  aboveFold?: boolean;
}

const LEAD_COUNT = 1;
const SECONDARY_COUNT = 4;

function variantFor(index: number, total: number, layout: "edited" | "list"): CardVariant {
  if (layout === "list") return "list";
  // A run too short to fill the secondary band would leave a lead card
  // stranded above one lonely row, so below that threshold everything stays
  // the same weight and the page just reads as a short list.
  if (total < LEAD_COUNT + SECONDARY_COUNT) return "secondary";
  if (index < LEAD_COUNT) return "lead";
  if (index < LEAD_COUNT + SECONDARY_COUNT) return "secondary";
  return "list";
}

export function FeedList({
  items,
  locale,
  surface,
  signedIn,
  revalidatePath,
  layout = "edited",
  aboveFold = false,
}: FeedListProps) {
  return (
    <ul className={`feed feed--${layout}`}>
      {items.map((item, index) => {
        const variant = variantFor(index, items.length, layout);
        return (
          <ArticleCard
            key={item.key ?? item.article.id}
            article={item.article}
            impressionId={item.impressionId}
            locale={locale}
            surface={surface}
            position={index}
            signedIn={signedIn}
            saved={item.saved}
            footnote={item.footnote}
            why={item.why}
            revalidatePath={revalidatePath}
            variant={variant}
            priority={aboveFold && index === 0}
          />
        );
      })}
    </ul>
  );
}
