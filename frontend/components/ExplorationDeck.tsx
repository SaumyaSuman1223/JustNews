import { ArticleCard } from "@/components/ArticleCard";
import type { DeckCard } from "@/lib/api";
import type { LocaleCode } from "@/lib/i18n";

/**
 * Stage 7's exploration deck: a grid of sample articles, stratified across
 * IPTC topics by the server (services.exploration_deck), that a reader
 * dismisses or engages with instead of checking topic boxes by hand.
 *
 * No new progression state, no swipe gestures - every card's dismiss-in-
 * place behaviour is exactly the existing ArticleActions/`card--hidden`
 * mechanism every other surface already uses. `variant="secondary"`, not
 * `"compact"`: a reader deciding whether something interests them benefits
 * from the image and snippet secondary cards carry, and the existing
 * `.feed` grid already responds down to one column on a phone - no new CSS
 * for this component at all.
 */
export function ExplorationDeck({
  cards,
  locale,
  signedIn,
}: {
  cards: DeckCard[];
  locale: LocaleCode;
  signedIn: boolean;
}) {
  return (
    <ul className="feed">
      {cards.map((card, index) => (
        <ArticleCard
          key={card.article.id}
          article={card.article}
          locale={locale}
          surface="onboarding"
          position={index}
          topicId={card.topic_id}
          impressionId={card.impression_id}
          signedIn={signedIn}
          revalidatePath={`/${locale}/onboarding`}
          variant="secondary"
        />
      ))}
    </ul>
  );
}
