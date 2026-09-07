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
  /**
   * How many items right after the lead band take §16's `feature` weight -
   * large image, large headline, full-width - before the run drops into
   * `secondaries`. Zero by default: most lists have no reason to interrupt
   * their own rhythm, so a call site states this explicitly the same way it
   * states `leads`, rather than the page guessing where variety would help.
   */
  features?: number;
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
  /**
   * Whether a multi-source story in this run may be promoted to §16's
   * `cluster` card (see `promoteOneCluster`). Off by default and turned on
   * explicitly at each call site that wants it - Home's tiers and its
   * ranked-continuation tabs - rather than on by default and turned off for
   * reader-curated sets: this repo has other `FeedList` callers (search, a
   * topic page, the edition archive) this chunk never reviewed, and a
   * default that silently changed their output the next time one of their
   * articles happened to cluster is exactly the kind of surprise an opt-in
   * avoids.
   */
  allowClusterPromotion?: boolean;
  /**
   * Fourth-pass §19: whether a story whose source carries an ADR 0013 role
   * may be promoted to the `perspective` card. Same opt-in reasoning as
   * `allowClusterPromotion` - a call site this pass never reviewed should not
   * silently change shape the day one of its sources gets a role assigned.
   */
  allowPerspectivePromotion?: boolean;
  /**
   * Audit §35's Home gesture ("expand a story / move from headline to
   * context"), applied to the run's own lead card only - Home's hero is the
   * one place this run has a single dominant story worth a second layer, and
   * every other `FeedList` caller (search, a topic feed, saved, history) has
   * no lead in the same sense. Off by default for the same opt-in reasons as
   * `allowClusterPromotion`.
   */
  expandableLead?: boolean;
}

const LEAD_COUNT = 1;
const SECONDARY_COUNT = 4;

function variantFor(
  index: number,
  total: number,
  layout: "edited" | "list",
  leads: number,
  features: number,
  secondaries: number,
  rest: "list" | "compact",
): CardVariant {
  if (layout === "list") return "list";
  // A run too short to fill every band would leave a lead or feature card
  // stranded above one lonely row, so below that threshold everything stays
  // the same weight and the page just reads as a short list.
  if (total < leads + features + secondaries) return "secondary";
  if (index < leads) return "lead";
  if (index < leads + features) return "feature";
  if (index < leads + features + secondaries) return "secondary";
  return rest;
}

/** A cluster counts as genuinely "developing" - worth `timeline` over the
 * plainer `cluster` - once there is real time between when it broke and when
 * it was last added to, not just a handful of sources filing within the same
 * hour. Six hours, not a shorter gap: same-hour multi-source coverage is
 * normal for any story with wire pickup and says nothing about development. */
const DEVELOPING_SPAN_MS = 6 * 60 * 60 * 1000;

/**
 * Audit §16's `cluster` card (and fourth-pass §19's `timeline`, a refinement
 * of it), chosen rather than assigned by position.
 *
 * Every other variant is a function of where an item falls in the run;
 * `cluster`/`timeline` are a function of what the ranker actually returned
 * that day - a multi-source story is real signal, not a slot the page
 * decided to have. Capped at one per list on purpose: promoting every
 * eligible item would make the page's rhythm depend on how many stories
 * happened to cluster today, which is exactly the "personalised must not
 * mean random" property the fixed variant set exists to hold onto. One
 * clustered story, treated once, reads as an editorial choice; several would
 * read as the layout losing control of itself. Only past the lead and
 * secondary bands, so the story that already earned the front of the run
 * keeps its own weight rather than being re-labelled on the way past.
 */
function promoteOneClusterOrTimeline(
  items: FeedItem[],
  variants: CardVariant[],
  leadsAndSecondaries: number,
): CardVariant[] {
  const eligible = items.findIndex(
    (item, index) => index >= leadsAndSecondaries && (item.article.coverage?.sources ?? 0) > 1,
  );
  if (eligible === -1) return variants;
  const coverage = items[eligible]?.article.coverage;
  const span = coverage
    ? Date.parse(coverage.last_seen_at) - Date.parse(coverage.first_seen_at)
    : 0;
  const promoted = [...variants];
  promoted[eligible] = span >= DEVELOPING_SPAN_MS ? "timeline" : "cluster";
  return promoted;
}

/**
 * Fourth-pass §19's `perspective` card - promoted the same way `cluster` is,
 * by a real signal (ADR 0013's assigned source role) rather than by position,
 * and capped at one per list for the same rhythm reason. Independent of the
 * cluster/timeline slot above: a story can be both widely covered and filed
 * by a roled source, but promoting the same card twice would just be one
 * card fighting itself over which fact it is presenting.
 */
function promoteOnePerspective(
  items: FeedItem[],
  variants: CardVariant[],
  leadsAndSecondaries: number,
): CardVariant[] {
  const eligible = items.findIndex(
    (item, index) =>
      index >= leadsAndSecondaries &&
      variants[index] !== "cluster" &&
      variants[index] !== "timeline" &&
      item.article.source_role &&
      item.article.source_role !== "wire",
  );
  if (eligible === -1) return variants;
  const promoted = [...variants];
  promoted[eligible] = "perspective";
  return promoted;
}

export function FeedList({
  items,
  locale,
  surface,
  signedIn,
  revalidatePath,
  layout = "edited",
  leads = LEAD_COUNT,
  features = 0,
  secondaries = SECONDARY_COUNT,
  rest = "list",
  aboveFold = false,
  allowClusterPromotion = false,
  allowPerspectivePromotion = false,
  expandableLead = false,
}: FeedListProps) {
  const baseVariants = items.map((_, index) =>
    variantFor(index, items.length, layout, leads, features, secondaries, rest),
  );
  const leadsAndSecondaries = layout === "edited" ? leads + features + secondaries : 0;
  const clusterVariants = allowClusterPromotion
    ? promoteOneClusterOrTimeline(items, baseVariants, leadsAndSecondaries)
    : baseVariants;
  const variants = allowPerspectivePromotion
    ? promoteOnePerspective(items, clusterVariants, leadsAndSecondaries)
    : clusterVariants;

  return (
    <ul className={`feed feed--${layout}`}>
      {items.map((item, index) => {
        const variant = variants[index];
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
            expandable={expandableLead && variant === "lead" && index === 0}
          />
        );
      })}
    </ul>
  );
}
