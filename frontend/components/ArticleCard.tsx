"use client";

import Image from "next/image";
import Link from "next/link";
import { useState } from "react";

import { ArticleActions } from "@/components/ArticleActions";
import type { Article } from "@/lib/api";
import { formatRelativeTime, locales, type LocaleCode } from "@/lib/i18n";
import { formatRankReason, type RankReason } from "@/lib/rankReason";

/**
 * The fixed card size set from docs/design/design-system.md.
 *
 * Fixed, and deliberately small: a ranked feed has to compose no matter what
 * order the ranker returns, and it can only do that if the slot shapes are
 * decided by the page rather than by the content. Principle 3 - "personalised
 * must not mean random" - is enforced here rather than hoped for.
 */
export type CardVariant = "lead" | "secondary" | "list" | "compact";

/** Image geometry per variant. Fixed, so nothing shifts while a photo loads. */
const MEDIA: Record<CardVariant, { width: number; height: number } | null> = {
  lead: { width: 1200, height: 675 },
  secondary: { width: 640, height: 360 },
  list: { width: 240, height: 160 },
  compact: null,
};

export interface ArticleCardProps {
  article: Article;
  locale: LocaleCode;
  /** Where this card was shown - logged with the click, for later analysis. */
  surface: "feed" | "explore" | "search" | "topic";
  position: number;
  /** The impression this card was served under, if any - lets a click be
   * attributed to the exact serving policy (Stage 5's A/B split) rather
   * than guessed at. Anonymous and non-feed surfaces have none. */
  impressionId?: number | null;
  /** Only a signed-in reader gets save / not-interested controls. */
  signedIn: boolean;
  saved?: boolean;
  /** Revalidated after a save/unsave/not-interested action. */
  revalidatePath: string;
  /** Extra context line under the metadata row, e.g. "Viewed 3 hours ago". */
  footnote?: string;
  /**
   * design-system.md's non-negotiable: "every ranked card can explain
   * itself." Undefined on every real route today - no surface has a reason
   * to give yet - so this renders nothing until a caller actually has one.
   * See lib/rankReason.ts.
   */
  why?: RankReason;
  variant?: CardVariant;
  /** Only the one card above the fold should preload its image. */
  priority?: boolean;
}

export function ArticleCard({
  article,
  locale,
  surface,
  position,
  impressionId,
  signedIn,
  saved = false,
  revalidatePath,
  footnote,
  why,
  variant = "secondary",
  priority = false,
}: ArticleCardProps) {
  // Owned here, not in ArticleActions: dimming is the card stepping its own
  // content back, and the confirmation text that explains why has to stay at
  // full contrast to say so - Artifact's pattern (the dismissed card grays
  // out in place) without losing the accessible status line this app's own
  // earlier pass added.
  const [hidden, setHidden] = useState(false);

  function handleClick() {
    // Fire-and-forget: never block or delay the navigation this accompanies.
    // Anonymous visits are a no-op server-side (see the route).
    void fetch("/api/click", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        articleId: article.id,
        surface,
        position,
        impressionId: impressionId ?? undefined,
      }),
      keepalive: true,
    });
  }

  const media = MEDIA[variant];
  // Named, not coded. A reader who chose two languages is told which one this
  // headline is in, in that language's own name - "Español", not "es". The
  // raw code survives only for a language outside the launch set, where the
  // corpus knows something the registry does not.
  const foreign =
    article.language === locale
      ? null
      : (locales.find((option) => option.code === article.language) ?? {
          label: article.language,
          htmlLang: article.language,
        });
  // The snippet is the first thing density costs you. A lead has room to
  // argue for itself; a list row has to survive on its headline.
  const showSnippet = (variant === "lead" || variant === "secondary") && Boolean(article.snippet);

  return (
    <li className={`card card--${variant}${hidden ? " card--hidden" : ""}`}>
      {media && article.image_url && (
        <div className="card__frame">
          <Image
            className="card__media"
            src={article.image_url}
            alt=""
            width={media.width}
            height={media.height}
            sizes={variant === "lead" ? "(max-width: 60rem) 100vw, 40rem" : "(max-width: 60rem) 50vw, 20rem"}
            unoptimized
            priority={priority}
          />
        </div>
      )}
      <div className="card__body">
        <h2 className="card__title">
          {/* The publisher link lives on the detail page, alongside related
              coverage - never fabricated full text, always a click away. */}
          <Link href={`/${locale}/a/${article.id}`} onClick={handleClick}>
            {article.title}
          </Link>
        </h2>
        {showSnippet && <p className="card__snippet">{article.snippet}</p>}
        <p className="card__meta">
          <span className="card__source">{article.source_name}</span>
          <time dateTime={article.published_at}>
            {formatRelativeTime(article.published_at, locale)}
          </time>
          {foreign && (
            <span className="badge" lang={foreign.htmlLang}>
              {foreign.label}
            </span>
          )}
        </p>
        {why && <p className="card__why">{formatRankReason(locale, why)}</p>}
        {footnote && <p className="card__footnote">{footnote}</p>}
        {signedIn && (
          <ArticleActions
            articleId={article.id}
            locale={locale}
            surface={surface}
            saved={saved}
            revalidatePath={revalidatePath}
            onHidden={() => setHidden(true)}
            onRestored={() => setHidden(false)}
          />
        )}
      </div>
    </li>
  );
}
