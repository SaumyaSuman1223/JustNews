"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { OutletIcon, originOf } from "@/components/discover/OutletIcon";
import { ExternalIcon, HeartIcon, MoreIcon, ShareIcon } from "@/components/icons";
import type { Article } from "@/lib/api";
import type { DiscoverItem } from "@/lib/discoverView";
import { formatRelativeTime, languageName, locales, t, tPlural, type LocaleCode } from "@/lib/i18n";
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
  /** Open at the publisher whatever the coverage (the story page). */
  openAtPublisher?: boolean;
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
  openAtPublisher = false,
}: StoryCardProps) {
  const { article } = item;
  const [hidden, setHidden] = useState(false);
  // A picture that does not load leaves a text card, not an empty frame.
  const [imageFailed, setImageFailed] = useState(false);
  useHydrated();
  const direct = openAtPublisher || opensAtPublisher(article);
  const href = direct ? article.url : `/${locale}/a/${article.id}`;

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

  // Generous enough for the widest page these cards sit on - a source or
  // story page has no rail, so its cards run wider than Discover's.
  const imageSizes =
    variant === "lead"
      ? "(max-width: 48rem) 100vw, 36rem"
      : variant === "wide"
        ? "(max-width: 48rem) 100vw, 30rem"
        : "(max-width: 40rem) 100vw, 24rem";

  return (
    <article className={`story story--${variant}`}>
      {article.image_url && !imageFailed && (
        <div className="story__media">
          <Image
            src={article.image_url}
            alt=""
            fill
            sizes={imageSizes}
            priority={priority}
            onError={() => setImageFailed(true)}
          />
        </div>
      )}
      <div className="story__body">
        <h2 className="story__title" lang={languageTag(article.language)}>
          {/* The stretched link: its ::after covers the card, so the whole
              card opens the article while the controls below stay their own
              targets. */}
          {direct ? (
            <a href={href} className="story__link" onClick={reportClick}>
              {article.title}
            </a>
          ) : (
            <Link href={href} className="story__link" onClick={reportClick}>
              {article.title}
            </Link>
          )}
        </h2>
        {(variant !== "card" || !article.image_url || imageFailed) && article.snippet && (
          <p className="story__snippet" lang={languageTag(article.language)}>
            {article.snippet}
          </p>
        )}
        <StoryMeta article={article} locale={locale} />
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
 * Whether a card opens the story at its publisher rather than on JustNews.
 * A story with one source in one language has nothing on JustNews's own
 * page but the card again, so the tap goes where the story is; one with
 * more coverage opens the page that shows it.
 */
export function opensAtPublisher(article: Article): boolean {
  const coverage = article.coverage;
  return !coverage || (coverage.sources <= 1 && coverage.languages <= 1);
}

/** The `lang` value for an article's language. */
function languageTag(code: string): string {
  return locales.find((option) => option.code === code)?.htmlLang ?? code;
}

/**
 * When the story was published, and which languages it is in: "3 hours ago
 * · also in Hindi, Spanish" for a story reported across languages, or the
 * card's own language when it is not the interface's - named in the
 * reader's language, since this is a sentence they have to read.
 */
function StoryMeta({ article, locale }: { article: Article; locale: LocaleCode }) {
  const others = (article.coverage?.language_codes ?? []).filter(
    (code) => code !== article.language,
  );
  // Named in the reader's language - "also in Hindi, Spanish" - since
  // this is a sentence the reader has to be able to read.
  const names = (codes: string[]) => codes.map((code) => languageName(code, locale)).join(", ");
  // "also in {languages}", with the names placed where each language's
  // grammar puts them ("{languages} में भी").
  const [before, after] = t(locale, "discover.alsoIn").split("{languages}");

  return (
    <p className="story__meta">
      <time dateTime={article.published_at} suppressHydrationWarning>
        {formatRelativeTime(article.published_at, locale)}
      </time>
      {others.length > 0 ? (
        <span className="story__langs">
          <span aria-hidden="true"> · </span>
          {before}
          {names(others)}
          {after}
        </span>
      ) : article.language !== locale ? (
        <span className="story__langs">
          <span aria-hidden="true"> · </span>
          {languageName(article.language, locale, { capitalize: true })}
        </span>
      ) : null}
    </p>
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
            // The article's own site is the publisher's: its favicon is the
            // outlet's, where a blank homepage fell back to an initial.
            homepage_url: originOf(article.url),
          },
        ];

  const content = (
    <>
      <span className="sources__icons" aria-hidden="true">
        {outlets.map((outlet) => (
          <OutletIcon key={outlet.slug} name={outlet.name} homepage={outlet.homepage_url} />
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
    return <SaveGate locale={locale} signedIn={signedIn} />;
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

/**
 * The heart for a reader who cannot save yet: it says why, and offers the
 * way in, instead of jumping to the login page and losing their place. The
 * sign-in link brings them back here.
 */
function SaveGate({ locale, signedIn }: { locale: LocaleCode; signedIn: boolean }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const [back, setBack] = useState(`/${locale}`);

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

  const label = t(locale, "discover.signInToSave");
  return (
    <div className="story__menu" ref={ref}>
      <button
        ref={trigger}
        type="button"
        className="story__action"
        aria-label={label}
        title={label}
        aria-expanded={open}
        onClick={() => {
          // Where to come back to after signing in: this page, as it is.
          setBack(window.location.pathname + window.location.search);
          setOpen((value) => !value);
        }}
      >
        <HeartIcon />
      </button>
      {open && (
        <div className="story__popover story__popover--note" role="note">
          <p>{t(locale, signedIn ? "discover.saveNeedsInvite" : "discover.saveNeedsAccount")}</p>
          {signedIn ? (
            <Link href={`/${locale}/invite`}>{t(locale, "discover.redeemInvite")}</Link>
          ) : (
            <Link href={`/${locale}/login?next=${encodeURIComponent(back)}`}>
              {t(locale, "account.signIn")}
            </Link>
          )}
        </div>
      )}
    </div>
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

  // Arrow keys move between the items, as in any menu a reader has used;
  // Tab still leaves it. Focus starts on the first item.
  const popover = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (open) popover.current?.querySelector<HTMLElement>("a, button")?.focus();
  }, [open]);
  function moveFocus(event: React.KeyboardEvent<HTMLDivElement>) {
    if (event.key !== "ArrowDown" && event.key !== "ArrowUp") return;
    event.preventDefault();
    const items = Array.from(event.currentTarget.querySelectorAll<HTMLElement>("a, button"));
    const index = items.indexOf(document.activeElement as HTMLElement);
    const step = event.key === "ArrowDown" ? 1 : -1;
    items[(index + step + items.length) % items.length]?.focus();
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
        <div className="story__popover" id={menuId} ref={popover} onKeyDown={moveFocus}>
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
