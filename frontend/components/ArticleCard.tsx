"use client";

import Image from "next/image";
import Link from "next/link";
import { useState } from "react";

import { ArticleActions } from "@/components/ArticleActions";
import type { Article } from "@/lib/api";
import {
  formatAbsoluteTime,
  formatArticleCoverage,
  formatRelativeTime,
  locales,
  t,
  type LocaleCode,
} from "@/lib/i18n";
import { formatRankReason, type RankReason } from "@/lib/rankReason";
import { useHydrated } from "@/lib/useHydrated";

/** ADR 0013's roles, in the same order and under the same labels
 * `Perspectives.tsx` uses - "wire" is deliberately absent from both: a wire
 * service is not a perspective. */
const ROLE_LABEL_KEY = {
  industry: "desk.perspectives.role.industry",
  government: "desk.perspectives.role.government",
  academic: "desk.perspectives.role.academic",
  investor: "desk.perspectives.role.investor",
  consumer: "desk.perspectives.role.consumer",
  public: "desk.perspectives.role.public",
} as const;

/**
 * The fixed card size set from docs/design/design-system.md.
 *
 * Fixed, and deliberately small: a ranked feed has to compose no matter what
 * order the ranker returns, and it can only do that if the slot shapes are
 * decided by the page rather than by the content. Principle 3 - "personalised
 * must not mean random" - is enforced here rather than hoped for.
 *
 * `cluster` is audit §16's fifth type - "one story connecting several
 * sources" - and it earns that description structurally, not just by label:
 * where every other variant leads with a picture or a headline, this one
 * leads with the coverage itself (see `formatArticleCoverage`), because the
 * fact that several newsrooms are reporting the same thing independently
 * *is* the story this card is telling.
 *
 * `feature` is §16's "large image + large headline": a full-width, stacked
 * treatment for a story a tier wants to give weight to without making it
 * *the* lead - assigned by position at the call site (`FeedList`'s
 * `features`), the same way `lead` and `secondary` are, because unlike
 * `cluster` there is no independent data signal that says "this one is a
 * feature" - only an editorial choice about where variety helps.
 *
 * `timeline` and `perspective` are fourth-pass §19's remaining story types,
 * chosen the same way `cluster` is - by what the data actually says, not by
 * position. `timeline` promotes a cluster that has genuinely developed over
 * time (see `promoteOneClusterOrTimeline` in FeedList); `perspective`
 * promotes an article whose source carries an assigned ADR 0013 role. Both
 * degrade to an ordinary card wherever their data is not there - see the
 * guards below, the same pattern `cluster`'s own coverage line already uses.
 */
export type CardVariant =
  | "lead"
  | "feature"
  | "secondary"
  | "list"
  | "compact"
  | "cluster"
  | "timeline"
  | "perspective";

/** Image geometry per variant. Fixed, so nothing shifts while a photo loads. */
const MEDIA: Record<CardVariant, { width: number; height: number } | null> = {
  lead: { width: 1200, height: 675 },
  feature: { width: 1200, height: 675 },
  secondary: { width: 640, height: 360 },
  list: { width: 240, height: 160 },
  compact: null,
  // No picture, on purpose: a cluster card's identity is the coverage line,
  // and a thumbnail here would just be one of the covering sources' photos
  // standing in for all the others, which overstates that one source.
  cluster: null,
  // Same reasoning as `cluster`: a timeline card's identity is when the
  // story developed, not which source's photo happened to run first.
  timeline: null,
  // A perspective card's identity is who is speaking - the role and the
  // publisher, in text, the same restraint the Perspectives module itself
  // uses (a list of sources, never a picture standing in for one of them).
  perspective: null,
};

export interface ArticleCardProps {
  article: Article;
  locale: LocaleCode;
  /** Where this card was shown - logged with the click, for later analysis. */
  surface: "feed" | "explore" | "search" | "topic" | "onboarding";
  position: number;
  /** The exploration deck's own topic for this card - only ever set on
   * surface="onboarding". Carried on the click report so
   * services.exploration_deck.record_deck_engagement can count it toward
   * the UserFollow bridge; every other surface leaves this unset. */
  topicId?: string;
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
  /**
   * Audit §35's Home gesture: "expand a story / move from headline to
   * context." Only meaningful on `lead` (Home's own hero sets it; nothing
   * else does), and only rendered when there is real context to reveal - the
   * exact publish instant always qualifies, the cluster's own coverage line
   * only when the story actually has one. No "why this matters" text: that
   * would be either an editorial voice this product doesn't have or a model
   * call in the request path, which ADR 0004 forbids.
   */
  expandable?: boolean;
}

export function ArticleCard({
  article,
  locale,
  surface,
  position,
  topicId,
  impressionId,
  signedIn,
  saved = false,
  revalidatePath,
  footnote,
  why,
  variant = "secondary",
  priority = false,
  expandable = false,
}: ArticleCardProps) {
  // Owned here, not in ArticleActions: dimming is the card stepping its own
  // content back, and the confirmation text that explains why has to stay at
  // full contrast to say so - Artifact's pattern (the dismissed card grays
  // out in place) without losing the accessible status line this app's own
  // earlier pass added.
  const [hidden, setHidden] = useState(false);
  const [expanded, setExpanded] = useState(false);
  // Relative times and the reader's local clock: re-rendered once after
  // hydration with the browser's own values (see useHydrated).
  useHydrated();

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
        topicId,
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
  const showSnippet =
    (variant === "lead" || variant === "feature" || variant === "secondary") &&
    Boolean(article.snippet);
  // Present whenever this card was actually promoted to `cluster` - see
  // FeedList, which only does that when `article.coverage.sources > 1`.
  // Guarded again here rather than trusted blindly: a `cluster`-variant card
  // whose coverage turned out to be a single source (data changed under it)
  // must still fall back to a normal byline instead of printing "1 sources".
  const coverageLine =
    (variant === "cluster" || variant === "timeline") &&
    article.coverage &&
    article.coverage.sources > 1
      ? formatArticleCoverage(locale, article.coverage)
      : null;
  // Same guard shape as `coverageLine`: only when FeedList actually promoted
  // this card (see `promoteOneClusterOrTimeline`), and re-checked here rather
  // than trusted, since a `timeline` card whose cluster no longer has a real
  // span must still read as a plain multi-source story instead of claiming
  // one that isn't there.
  const developingSince =
    variant === "timeline" && article.coverage
      ? formatRelativeTime(article.coverage.first_seen_at, locale)
      : null;
  // Present whenever FeedList promoted this card to `perspective` (see
  // `promoteOnePerspective`) and the source still carries a role §21/ADR
  // 0013 recognises - the same six roles `Perspectives.tsx` groups by,
  // "wire" excluded on purpose in both places.
  const roleLabelKey =
    variant === "perspective" && article.source_role
      ? ROLE_LABEL_KEY[article.source_role as keyof typeof ROLE_LABEL_KEY]
      : undefined;
  const showContextToggle = variant === "lead" && expandable;
  const contextId = `lead-context-${article.id}`;

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
            sizes={
              variant === "lead" || variant === "feature"
                ? "(max-width: 60rem) 100vw, 40rem"
                : "(max-width: 60rem) 50vw, 20rem"
            }
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
        {developingSince && (
          // A timeline card leads with when the story developed, not who
          // filed the article this card happens to link - the coverage line
          // right below it (same markup `cluster` uses) still says how widely.
          <p className="card__developing" suppressHydrationWarning>
            {t(locale, "card.timeline.developing", { time: developingSince })}
          </p>
        )}
        {coverageLine ? (
          // The coverage line replaces the byline entirely rather than
          // sitting beside it: "reported by 7 sources across 4 countries"
          // and "The Standard · 5h ago" are two different claims about the
          // same story, and printing both invites a reader to wonder which
          // one this card is actually about.
          <p className="card__coverage">{coverageLine}</p>
        ) : roleLabelKey ? (
          // A perspective card's byline leads with the role, not the outlet -
          // "Industry press · Trade Daily" says who is speaking before it says
          // which publication, the same order the Perspectives module itself
          // groups by.
          <p className="card__meta card__meta--role">
            <span className="card__role">{t(locale, roleLabelKey)}</span>
            <span className="card__source">{article.source_name}</span>
            <time dateTime={article.published_at} suppressHydrationWarning>
              {formatRelativeTime(article.published_at, locale)}
            </time>
          </p>
        ) : (
          <p className="card__meta">
            <span className="card__source">{article.source_name}</span>
            <time dateTime={article.published_at} suppressHydrationWarning>
              {formatRelativeTime(article.published_at, locale)}
            </time>
            {foreign && (
              <span className="badge" lang={foreign.htmlLang}>
                {foreign.label}
              </span>
            )}
          </p>
        )}
        {showContextToggle && (
          <>
            <button
              type="button"
              className="card__context-toggle"
              aria-expanded={expanded}
              aria-controls={contextId}
              onClick={() => setExpanded((value) => !value)}
            >
              {t(locale, expanded ? "home.lead.context.hide" : "home.lead.context.show")}
            </button>
            <div
              className="card__context"
              id={contextId}
              data-expanded={expanded || undefined}
              // Collapsed content stays in the DOM (so the height transition
              // has something to animate) but must not be reachable - `hidden`
              // would also block the transition, so `inert` is what keeps a
              // keyboard or screen reader user from landing on the link
              // inside while it is visually collapsed to nothing.
              inert={!expanded}
            >
              <div className="card__context-inner">
                <p suppressHydrationWarning>
                  {t(locale, "home.lead.context.published", {
                    time: formatAbsoluteTime(article.published_at, locale),
                  })}
                </p>
                {article.coverage && article.coverage.sources > 1 && (
                  <p>
                    {formatArticleCoverage(locale, article.coverage)}
                    {article.story_cluster_id && (
                      <>
                        {" · "}
                        <Link href={`/${locale}/story/${article.story_cluster_id}`}>
                          {t(locale, "home.lead.context.coverage")}
                        </Link>
                      </>
                    )}
                  </p>
                )}
              </div>
            </div>
          </>
        )}
        {why && <p className="card__why">{formatRankReason(locale, why)}</p>}
        {footnote && <p className="card__footnote">{footnote}</p>}
        {signedIn && (
          <ArticleActions
            articleId={article.id}
            locale={locale}
            surface={surface}
            topicId={topicId}
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
