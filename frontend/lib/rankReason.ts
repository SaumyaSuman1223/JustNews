import { t, type LocaleCode } from "@/lib/i18n";

/**
 * Why a ranked card is where it is, as the API reports it (`reason` on a
 * feed or Discover item) - with the topic resolved to a label for display.
 *
 * Each kind is a term ranker v2 actually applied (ADR 0015): a followed
 * story, topic or source; closeness to what the reader has been reading;
 * click-through strong enough to call a trend; or an exploration slot
 * (design-system.md: "a visible exploration slot so discovery is legible
 * rather than mysterious"). A card placed on recency alone has no reason
 * and shows none. Nothing here claims a model's internal reasoning - a
 * learned ranker is a different, harder disclosure problem.
 */
export type RankReason =
  | { kind: "followed_topic"; topic: string }
  | { kind: "followed_source" }
  | { kind: "followed_story" }
  | { kind: "similar" }
  | { kind: "trending" }
  | { kind: "exploration" };

export function formatRankReason(locale: LocaleCode, reason: RankReason): string {
  switch (reason.kind) {
    case "followed_topic":
      return t(locale, "card.why.followedTopic", { topic: reason.topic });
    case "followed_source":
      return t(locale, "card.why.followedSource");
    case "followed_story":
      return t(locale, "card.why.followedStory");
    case "similar":
      return t(locale, "card.why.similar");
    case "trending":
      return t(locale, "card.why.trending");
    case "exploration":
      return t(locale, "card.why.exploration");
  }
}
