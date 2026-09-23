import { t, type LocaleCode } from "@/lib/i18n";

/**
 * Why a ranked card is where it is, as the feed API reports it
 * (`FeedItemOut.reason`, fifth pass F7) - with the topic resolved to a label
 * for display.
 *
 * Three kinds, each a factor the Stage 5 heuristic ranker actually applied:
 * a followed-topic boost, a popularity count large enough to call a trend,
 * or the exploration slice design-system.md calls for ("a visible
 * exploration slot so discovery is legible rather than mysterious"). A card
 * placed on recency alone has no reason and shows none. Nothing here claims
 * a model's internal reasoning - Stage 6 is a different, harder disclosure
 * problem this type does not attempt to solve.
 */
export type RankReason =
  | { kind: "followed_topic"; topic: string }
  | { kind: "trending" }
  | { kind: "exploration" };

export function formatRankReason(locale: LocaleCode, reason: RankReason): string {
  switch (reason.kind) {
    case "followed_topic":
      return t(locale, "card.why.followedTopic", { topic: reason.topic });
    case "trending":
      return t(locale, "card.why.trending");
    case "exploration":
      return t(locale, "card.why.exploration");
  }
}
