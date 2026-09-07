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
  /**
   * How many of the run take the lead and secondary weights. Defaults are the
   * front-page shape; Home's tiers set them explicitly, because a tier is
   * defined by how prominent its stories are and that should be stated at the
   * call site rather than inferred from how many happen to be in the list.
   */
  leads?: number;
  secondaries?: number;
  /**
   * What everything past the lead and secondary bands takes.
   *
   * `list` is a headline with a thumbnail - the right shape for a stream that
   * continues indefinitely. `compact` is a headline and its source with no
   * image at all, which is what audit §18 and §32 are asking for: a band of
   * text-dominant entries so a section is not six copies of the same card.
   */
  rest?: "list" | "compact";
  /** Set on the first screenful of the page, so the lead image preloads. */
  aboveFold?: boolean;
}

const LEAD_COUNT = 1;
const SECONDARY_COUNT = 4;

function variantFor(
  index: number,
  total: number,
  layout: "edited" | "list",
  leads: number,
  secondaries: number,
  rest: "list" | "compact",
): CardVariant {
  if (layout === "list") return "list";
  // A run too short to fill the secondary band would leave a lead card
  // stranded above one lonely row, so below that threshold everything stays
  // the same weight and the page just reads as a short list.
  if (total < leads + secondaries) return "secondary";
  if (index < leads) return "lead";
  if (index < leads + secondaries) return "secondary";
  return rest;
}

export function FeedList({
  items,
  locale,
  surface,
  signedIn,
  revalidatePath,
  layout = "edited",
  leads = LEAD_COUNT,
  secondaries = SECONDARY_COUNT,
  rest = "list",
  aboveFold = false,
}: FeedListProps) {
  return (
    <ul className={`feed feed--${layout}`}>
      {items.map((item, index) => {
        const variant = variantFor(index, items.length, layout, leads, secondaries, rest);
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
