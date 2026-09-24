"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { ClockIcon, ExternalIcon, HeartIcon, MoreIcon, ShareIcon } from "@/components/icons";
import type { Article } from "@/lib/api";
import type { DiscoverItem } from "@/lib/discoverView";
import { formatRelativeTime, t, tPlural, type LocaleCode } from "@/lib/i18n";
import { formatRankReason } from "@/lib/rankReason";
import { useHydrated } from "@/lib/useHydrated";

export type StoryVariant = "lead" | "card" | "wide";

export interface StoryCardProps {
  item: DiscoverItem;
  variant: StoryVariant;
  locale: LocaleCode;
  position: number;
  surface: "feed" | "topic";
  signedIn: boolean;
  canPersonalise: boolean;
  saved: boolean;
  onSavedChange: (articleId: number, saved: boolean) => void;
  priority?: boolean;
}

/**
 * One story on Discover, in one of the feed's three shapes: the lead (text
 * beside a large picture), a card in a row of three, or a wide feature
 * (picture beside text). The whole card is a link to the article page; the
 * sources line and the actions sit above that link, so each is its own
 * target.
 *
 * Original reporting only: the headline and the publisher's own snippet,
 * never a summary (ADR 0004), with "N sources" leading to every outlet on
 * the story.
 */
export function StoryCard({
  item,
  variant,
  locale,
  position,
  surface,
  signedIn,
  canPersonalise,
  saved,
  onSavedChange,
  priority = false,
}: StoryCardProps) {
  const { article } = item;
  const [hidden, setHidden] = useState(false);
  useHydrated();
  const href = `/${locale}/a/${article.id}`;

  function reportClick() {
    // Fire-and-forget, never delaying the navigation. Anonymous reads are a
    // no-op server-side.
    void fetch("/api/click", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        articleId: article.id,
        surface,
        position,
        impressionId: item.impressionId ?? undefined,
      }),
      keepalive: true,
    });
  }

  if (hidden) {
    return (
      <article className={`story story--${variant} story--hidden`}>
        <p role="status">{t(locale, "discover.hidden")}</p>
        <UndoHide
          locale={locale}
          articleId={article.id}
          surface={surface}
          onRestored={() => setHidden(false)}
        />
      </article>
    );
  }

  const imageSizes =
    variant === "lead"
      ? "(max-width: 48rem) 100vw, 26rem"
      : variant === "wide"
        ? "(max-width: 48rem) 100vw, 22rem"
        : "(max-width: 48rem) 100vw, 16rem";

  return (
    <article className={`story story--${variant}`}>
      {article.image_url && (
        <div className="story__media">
          <Image
            src={article.image_url}
            alt=""
            fill
            sizes={imageSizes}
            unoptimized
            priority={priority}
          />
        </div>
      )}
      <div className="story__body">
        <h2 className="story__title">
          {/* The stretched link: its ::after covers the card, so the whole
              card opens the article while the controls below stay their own
              targets. */}
          <Link href={href} className="story__link" onClick={reportClick}>
            {article.title}
          </Link>
        </h2>
        {variant === "lead" && (
          <p className="story__published" suppressHydrationWarning>
            <ClockIcon className="story__clock" />
            {t(locale, "discover.published", {
              time: formatRelativeTime(article.published_at, locale),
            })}
          </p>
        )}
        {(variant !== "card" || !article.image_url) && article.snippet && (
          <p className="story__snippet">{article.snippet}</p>
        )}
        {item.why && <p className="story__why">{formatRankReason(locale, item.why)}</p>}
        <div className="story__foot">
          <SourcesLine article={article} locale={locale} />
          <div className="story__actions">
            <SaveHeart
              locale={locale}
              articleId={article.id}
              signedIn={signedIn}
              canSave={canPersonalise}
              saved={saved}
              onChange={onSavedChange}
            />
            <MoreMenu
              locale={locale}
              article={article}
              surface={surface}
              canPersonalise={canPersonalise}
              onHidden={() => setHidden(true)}
            />
          </div>
        </div>
      </div>
    </article>
  );
}

/**
 * "26 sources" with the favicons of the first few - a real count from the
 * story cluster, leading to the story page that lists every outlet. A story
 * with one source names that outlet instead, and leads to its page.
 */
function SourcesLine({ article, locale }: { article: Article; locale: LocaleCode }) {
  const coverage = article.coverage;
  const many = coverage && coverage.sources > 1 && article.story_cluster_id !== null;
  const outlets =
    many && coverage.outlets && coverage.outlets.length > 0
      ? coverage.outlets
      : [
          {
            slug: article.source_slug,
            name: article.source_name,
            homepage_url: "",
          },
        ];

  const content = (
    <>
      <span className="sources__icons" aria-hidden="true">
        {outlets.map((outlet) => (
          <Favicon key={outlet.slug} name={outlet.name} homepage={outlet.homepage_url} />
        ))}
      </span>
      <span className="sources__label">
        {many ? tPlural(locale, "coverage.sources", coverage.sources) : article.source_name}
      </span>
    </>
  );

  return many ? (
    <Link className="sources" href={`/${locale}/story/${article.story_cluster_id}`}>
      {content}
    </Link>
  ) : (
    <Link className="sources" href={`/${locale}/source/${encodeURIComponent(article.source_slug)}`}>
      {content}
    </Link>
  );
}

/** The outlet's own favicon, from its own site - the same hotlinking the
 * product already does for article images. Its initial when there is no
 * homepage to ask, or the icon does not load. */
function Favicon({ name, homepage }: { name: string; homepage: string }) {
  const [failed, setFailed] = useState(false);
  let src: string | null = null;
  if (homepage) {
    try {
      src = new URL("/favicon.ico", homepage).toString();
    } catch {
      src = null;
    }
  }
  if (!src || failed) {
    return <span className="sources__icon sources__icon--letter">{name.slice(0, 1)}</span>;
  }
  return (
    <Image
      className="sources__icon"
      src={src}
      alt=""
      width={18}
      height={18}
      unoptimized
      onError={() => setFailed(true)}
    />
  );
}

function SaveHeart({
  locale,
  articleId,
  signedIn,
  canSave,
  saved,
  onChange,
}: {
  locale: LocaleCode;
  articleId: number;
  signedIn: boolean;
  canSave: boolean;
  saved: boolean;
  onChange: (articleId: number, saved: boolean) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);

  if (!signedIn || !canSave) {
    return (
      <Link
        className="story__action"
        href={`/${locale}/login`}
        aria-label={t(locale, "discover.signInToSave")}
        title={t(locale, "discover.signInToSave")}
      >
        <HeartIcon />
      </Link>
    );
  }

  async function toggle() {
    const next = !saved;
    setBusy(true);
    setFailed(false);
    // Optimistic: the heart answers at once, and turns back if the save did
    // not happen - a failed save must not look like a successful one.
    onChange(articleId, next);
    try {
      const response = await fetch("/api/saves", {
        method: next ? "POST" : "DELETE",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ articleId }),
      });
      if (!response.ok) throw new Error(String(response.status));
    } catch {
      onChange(articleId, !next);
      setFailed(true);
    } finally {
      setBusy(false);
    }
  }

  const label = t(locale, saved ? "discover.unsave" : "discover.save");
  return (
    <>
      <button
        type="button"
        className="story__action"
        data-shortcut="save"
        data-active={saved || undefined}
        aria-pressed={saved}
        aria-label={label}
        title={label}
        disabled={busy}
        onClick={toggle}
      >
        <HeartIcon filled={saved} />
      </button>
      {failed && (
        <span className="visually-hidden" role="alert">
          {t(locale, "discover.actionFailed")}
        </span>
      )}
    </>
  );
}

function MoreMenu({
  locale,
  article,
  surface,
  canPersonalise,
  onHidden,
}: {
  locale: LocaleCode;
  article: Article;
  surface: "feed" | "topic";
  canPersonalise: boolean;
  onHidden: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    function onPointer(event: PointerEvent) {
      if (!ref.current?.contains(event.target as Node)) setOpen(false);
    }
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
        trigger.current?.focus();
      }
    }
    document.addEventListener("pointerdown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("pointerdown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  async function share() {
    const url = new URL(`/${locale}/a/${article.id}`, window.location.origin).toString();
    try {
      if (navigator.share) {
        await navigator.share({ title: article.title, url });
      } else {
        await navigator.clipboard.writeText(url);
        setCopied(true);
      }
    } catch {
      // The reader closed the share sheet; nothing to report.
    }
    setOpen(false);
  }

  async function notInterested() {
    setOpen(false);
    const response = await fetch("/api/not-interested", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ articleId: article.id, surface }),
    }).catch(() => null);
    if (response?.ok) onHidden();
  }

  const menuId = `story-menu-${article.id}`;
  return (
    <div className="story__menu" ref={ref}>
      <button
        ref={trigger}
        type="button"
        className="story__action"
        aria-label={t(locale, "discover.more")}
        title={t(locale, "discover.more")}
        aria-expanded={open}
        aria-controls={menuId}
        onClick={() => setOpen((value) => !value)}
      >
        <MoreIcon />
      </button>
      {copied && (
        <span className="story__toast" role="status">
          {t(locale, "discover.copied")}
        </span>
      )}
      {open && (
        // A disclosure of plain links and buttons, not an ARIA menu - the
        // earlier pass removed a fake one; tabbing through these is honest.
        <div className="story__popover" id={menuId}>
          <button type="button" onClick={share}>
            <ShareIcon />
            {t(locale, "discover.share")}
          </button>
          <a href={article.url} target="_blank" rel="noopener noreferrer">
            <ExternalIcon />
            {t(locale, "discover.openOriginal", { source: article.source_name })}
          </a>
          {article.story_cluster_id !== null && (
            <Link href={`/${locale}/story/${article.story_cluster_id}`}>
              {t(locale, "discover.allSources")}
            </Link>
          )}
          {canPersonalise && (
            <button type="button" onClick={notInterested}>
              {t(locale, "discover.notInterested")}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function UndoHide({
  locale,
  articleId,
  surface,
  onRestored,
}: {
  locale: LocaleCode;
  articleId: number;
  surface: "feed" | "topic";
  onRestored: () => void;
}) {
  async function undo() {
    const response = await fetch("/api/not-interested", {
      method: "DELETE",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ articleId, surface }),
    }).catch(() => null);
    if (response?.ok) onRestored();
  }
  return (
    <button type="button" className="story__undo" onClick={undo}>
      {t(locale, "discover.undo")}
    </button>
  );
}
