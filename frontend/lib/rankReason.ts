import { t, type LocaleCode } from "@/lib/i18n";

/**
 * Why a ranked card is where it is - a mock shape today, not a live one.
 * `FeedItemOut` (packages/api-client/src/schema.ts) carries no reason field
 * yet; Stage 5 is what will compute one. This type is the contract that
 * field is expected to satisfy, written first so ArticleCard's rendering
 * needs no rework once it is real - see app/[locale]/dev/why/page.tsx for
 * where this is exercised today, and PRODUCT.md for why nowhere else is.
 *
 * Four kinds, matched to what a heuristic ranker (Stage 5) could plausibly
 * explain about itself: an explicit follow, recency-weighted popularity, or
 * the exploration slice design-system.md calls for ("a visible exploration
 * slot so discovery is legible rather than mysterious"). Nothing here claims
 * a model's internal reasoning - Stage 6 is a different, harder disclosure
 * problem this type does not attempt to solve.
 */
export type RankReason =
  | { kind: "followed_topic"; topic: string }
  | { kind: "followed_source"; source: string }
  | { kind: "trending" }
  | { kind: "exploration" };

export function formatRankReason(locale: LocaleCode, reason: RankReason): string {
  switch (reason.kind) {
    case "followed_topic":
      return t(locale, "card.why.followedTopic", { topic: reason.topic });
    case "followed_source":
      return t(locale, "card.why.followedSource", { source: reason.source });
    case "trending":
      return t(locale, "card.why.trending");
    case "exploration":
      return t(locale, "card.why.exploration");
  }
}
