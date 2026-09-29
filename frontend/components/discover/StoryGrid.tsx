"use client";

import { useMemo, useState } from "react";

import { StoryCard } from "@/components/discover/StoryCard";
import { arrange } from "@/components/discover/storyLayout";
import type { Article } from "@/lib/api";
import type { LocaleCode } from "@/lib/i18n";

/**
 * Discover's cards, for any page with a list of stories - a publisher's
 * latest, a story's coverage in one language, "More from" under an
 * article - so every list in the product is the same object as the front
 * page's, not an older design beside it.
 */
export function StoryGrid({
  articles,
  locale,
  surface,
  signedIn,
  canPersonalise,
  initialSaved = [],
  lead = true,
  features = true,
  firstPosition = 0,
  openAtPublisher = false,
}: {
  articles: Article[];
  locale: LocaleCode;
  surface: "feed" | "topic";
  signedIn: boolean;
  canPersonalise: boolean;
  initialSaved?: number[];
  lead?: boolean;
  features?: boolean;
  /** Where these cards start in the page's order, for click positions. */
  firstPosition?: number;
  /** Every card opens at its publisher - on a page that is itself the
   * story's coverage. */
  openAtPublisher?: boolean;
}) {
  const [saved, setSaved] = useState(() => new Set(initialSaved));
  const blocks = useMemo(
    () =>
      arrange(
        articles.map((article) => ({ article, impressionId: null, why: null })),
        { lead, features },
      ),
    [articles, lead, features],
  );

  function onSavedChange(articleId: number, isSaved: boolean) {
    setSaved((current) => {
      const next = new Set(current);
      if (isSaved) next.add(articleId);
      else next.delete(articleId);
      return next;
    });
  }

  return (
    <div className="story-grid">
      {blocks.map((block, blockIndex) => (
        <div className={`discover__block discover__block--${block.variant}`} key={blockIndex}>
          {block.items.map(({ item, position }) => (
            <StoryCard
              key={item.article.id}
              item={item}
              variant={block.variant}
              locale={locale}
              position={firstPosition + position}
              surface={surface}
              signedIn={signedIn}
              canPersonalise={canPersonalise}
              saved={saved.has(item.article.id)}
              onSavedChange={onSavedChange}
              openAtPublisher={openAtPublisher}
            />
          ))}
        </div>
      ))}
    </div>
  );
}
