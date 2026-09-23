"use client";

import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { StoryCard, type StoryVariant } from "@/components/discover/StoryCard";
import { ChevronDownIcon } from "@/components/icons";
import {
  parseView,
  viewHref,
  viewKey,
  viewQuery,
  type DiscoverItem,
  type DiscoverPage,
  type DiscoverView,
} from "@/lib/discoverView";
import { t, type LocaleCode } from "@/lib/i18n";

/** A view revisited within this long is shown as it was; older than this,
 * it is shown and quietly refreshed. */
const FRESH_MS = 3 * 60 * 1000;
/** Start fetching the next page this far before the reader reaches it. */
const PREFETCH_MARGIN = "1400px";

type Entry = {
  items: DiscoverItem[];
  nextCursor: string | null;
  fetchedAt: number;
  error: boolean;
};

/**
 * Kept for the life of the tab, across route changes, so going back to
 * Discover from an article - or back to a tab already seen - is instant. A
 * module-level map rather than a context: nothing else reads it.
 */
const cache = new Map<string, Entry>();

export interface DiscoverTopic {
  id: string;
  label: string;
}

/**
 * Discover: For You, Top and a topic, as one feed that swaps in place.
 *
 * The server renders the first page of whichever view the URL names, so the
 * page is complete before any JavaScript. After that, changing view is a
 * `history.pushState` - the URL stays shareable and Back works - and the
 * page comes from /api/discover, or from memory if the reader has seen it.
 * Scrolling fetches the next cursor page well before the end.
 */
export function Discover({
  locale,
  initialView,
  initialPage,
  topics,
  signedIn,
  canPersonalise,
  initialSaved,
}: {
  locale: LocaleCode;
  initialView: DiscoverView;
  initialPage: DiscoverPage;
  topics: DiscoverTopic[];
  signedIn: boolean;
  canPersonalise: boolean;
  initialSaved: number[];
}) {
  const searchParams = useSearchParams();
  const view = parseView({ view: searchParams.get("view"), topic: searchParams.get("topic") });
  const key = viewKey(view);

  // The server's page seeds the cache once, under the view it rendered.
  useState(() => seed(initialView, initialPage));

  const [, setVersion] = useState(0);
  const rerender = useCallback(() => setVersion((value) => value + 1), []);
  const [saved, setSaved] = useState(() => new Set(initialSaved));
  // In flight, as `view|cursor`. State rather than a ref, because the
  // "loading more" line renders from it.
  const [pending, setPending] = useState<ReadonlySet<string>>(() => new Set());
  const inFlight = useRef(new Set<string>());

  const load = useCallback(
    async (target: DiscoverView, cursor?: string) => {
      const targetKey = viewKey(target);
      const loadingKey = `${targetKey}|${cursor ?? ""}`;
      if (inFlight.current.has(loadingKey)) return;
      inFlight.current.add(loadingKey);
      setPending(new Set(inFlight.current));
      try {
        const query = viewQuery(target);
        query.set("locale", locale);
        if (cursor) query.set("cursor", cursor);
        const response = await fetch(`/api/discover?${query}`);
        if (!response.ok) throw new Error(String(response.status));
        const page = (await response.json()) as DiscoverPage;
        const previous = cursor ? cache.get(targetKey) : undefined;
        // Later pages can repeat a story the first page's importance order
        // already placed; each article is shown once.
        const seen = new Set(previous?.items.map((item) => item.article.id));
        cache.set(targetKey, {
          items: [
            ...(previous?.items ?? []),
            ...page.items.filter((item) => !seen.has(item.article.id)),
          ],
          nextCursor: page.nextCursor,
          fetchedAt: previous?.fetchedAt ?? Date.now(),
          error: false,
        });
      } catch {
        const previous = cache.get(targetKey);
        cache.set(targetKey, {
          items: previous?.items ?? [],
          nextCursor: previous?.nextCursor ?? null,
          fetchedAt: previous?.fetchedAt ?? 0,
          error: true,
        });
      } finally {
        inFlight.current.delete(loadingKey);
        setPending(new Set(inFlight.current));
        rerender();
      }
    },
    [locale, rerender],
  );

  const entry = cache.get(key);

  // A view not in memory is fetched; one in memory but old is refreshed
  // behind what is already on screen.
  useEffect(() => {
    const current = cache.get(key);
    if (!current || (!current.error && Date.now() - current.fetchedAt > FRESH_MS)) {
      if (current) cache.delete(key);
      void load(view);
    }
    // `view` is derived from `key`; depending on the string keeps this from
    // running on every render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, load]);

  function go(next: DiscoverView) {
    if (viewKey(next) === key) return;
    window.history.pushState(null, "", viewHref(locale, next));
    window.scrollTo({ top: 0 });
  }

  function onSavedChange(articleId: number, isSaved: boolean) {
    setSaved((current) => {
      const next = new Set(current);
      if (isSaved) next.add(articleId);
      else next.delete(articleId);
      return next;
    });
  }

  const sentinel = useRef<HTMLDivElement>(null);
  const nextCursor = entry?.nextCursor ?? null;
  const pagePending = nextCursor !== null && pending.has(`${key}|${nextCursor}`);
  useEffect(() => {
    const element = sentinel.current;
    if (!element || !nextCursor) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((item) => item.isIntersecting)) void load(view, nextCursor);
      },
      { rootMargin: PREFETCH_MARGIN },
    );
    observer.observe(element);
    return () => observer.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, nextCursor, load]);

  const surface = view.kind === "topic" ? "topic" : "feed";
  const blocks = useMemo(() => arrange(entry?.items ?? []), [entry?.items]);

  return (
    <div className="discover">
      <DiscoverTabs locale={locale} view={view} topics={topics} onChange={go} />

      <div className="discover__feed" key={key} aria-busy={!entry || undefined}>
        {!entry ? (
          <FeedSkeleton />
        ) : entry.items.length === 0 ? (
          entry.error ? (
            <FeedError locale={locale} onRetry={() => void load(view)} />
          ) : (
            <p className="discover__empty">{t(locale, "discover.empty")}</p>
          )
        ) : (
          <>
            {blocks.map((block, blockIndex) => (
              <div className={`discover__block discover__block--${block.variant}`} key={blockIndex}>
                {block.items.map(({ item, position }) => (
                  <StoryCard
                    key={item.article.id}
                    item={item}
                    variant={block.variant}
                    locale={locale}
                    position={position}
                    surface={surface}
                    signedIn={signedIn}
                    canPersonalise={canPersonalise}
                    saved={saved.has(item.article.id)}
                    onSavedChange={onSavedChange}
                    priority={position === 0}
                  />
                ))}
              </div>
            ))}
            <div ref={sentinel} className="discover__sentinel" aria-hidden="true" />
            {entry.error ? (
              <FeedError
                locale={locale}
                onRetry={() => void load(view, entry.nextCursor ?? undefined)}
              />
            ) : pagePending ? (
              <p className="discover__status" role="status">
                <span className="discover__spinner" aria-hidden="true" />
                {t(locale, "discover.loadingMore")}
              </p>
            ) : entry.nextCursor === null ? (
              <p className="discover__status">{t(locale, "discover.end")}</p>
            ) : null}
          </>
        )}
      </div>
    </div>
  );
}

function seed(view: DiscoverView, page: DiscoverPage): true {
  const key = viewKey(view);
  const existing = cache.get(key);
  if (!existing || Date.now() - existing.fetchedAt > FRESH_MS) {
    cache.set(key, {
      items: page.items,
      nextCursor: page.nextCursor,
      fetchedAt: Date.now(),
      error: false,
    });
  }
  return true;
}

type Block = { variant: StoryVariant; items: { item: DiscoverItem; position: number }[] };

/**
 * The feed's rhythm: one lead, then a row of three cards and a wide feature,
 * repeating. A picture-less story never takes the lead or the feature slot
 * when one with a picture is near - those shapes are built around the photo.
 */
function arrange(items: DiscoverItem[]): Block[] {
  const queue = items.map((item, position) => ({ item, position }));
  const blocks: Block[] = [];
  // Only called while the queue is non-empty, so `splice` always yields one.
  const takeWithImage = () => {
    const index = queue.findIndex((entry, i) => i < 4 && entry.item.article.image_url);
    return queue.splice(index >= 0 ? index : 0, 1);
  };
  if (queue.length > 0) blocks.push({ variant: "lead", items: takeWithImage() });
  while (queue.length > 0) {
    blocks.push({ variant: "card", items: queue.splice(0, 3) });
    if (queue.length > 0) blocks.push({ variant: "wide", items: takeWithImage() });
  }
  return blocks;
}

function DiscoverTabs({
  locale,
  view,
  topics,
  onChange,
}: {
  locale: LocaleCode;
  view: DiscoverView;
  topics: DiscoverTopic[];
  onChange: (view: DiscoverView) => void;
}) {
  const [open, setOpen] = useState(false);
  const menu = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const activeTopic =
    view.kind === "topic" ? topics.find((topic) => topic.id === view.topicId) : undefined;

  useEffect(() => {
    if (!open) return;
    function onPointer(event: PointerEvent) {
      if (!menu.current?.contains(event.target as Node)) setOpen(false);
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

  // Real links, so each view can be opened in a new tab or shared; a plain
  // click is intercepted and handled in place.
  function linkProps(target: DiscoverView) {
    return {
      href: viewHref(locale, target),
      onClick: (event: React.MouseEvent<HTMLAnchorElement>) => {
        if (event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) return;
        event.preventDefault();
        setOpen(false);
        onChange(target);
      },
    };
  }

  return (
    <div className="discover__bar">
      <h1 className="discover__title">{t(locale, "discover.title")}</h1>
      <nav className="discover__tabs" aria-label={t(locale, "discover.tabs")}>
        <a
          className="discover__tab"
          aria-current={view.kind === "for-you" ? "page" : undefined}
          {...linkProps({ kind: "for-you" })}
        >
          {t(locale, "discover.tab.forYou")}
        </a>
        <a
          className="discover__tab"
          aria-current={view.kind === "top" ? "page" : undefined}
          {...linkProps({ kind: "top" })}
        >
          {t(locale, "discover.tab.top")}
        </a>
        <div className="discover__topics" ref={menu}>
          <button
            ref={trigger}
            type="button"
            className="discover__tab"
            aria-current={view.kind === "topic" ? "page" : undefined}
            aria-expanded={open}
            aria-controls="discover-topics"
            onClick={() => setOpen((value) => !value)}
          >
            {activeTopic?.label ?? t(locale, "discover.tab.topics")}
            <ChevronDownIcon className="discover__chevron" />
          </button>
          {open && (
            <ul className="discover__topic-list" id="discover-topics">
              {topics.map((topic) => (
                <li key={topic.id}>
                  <a
                    className="discover__topic"
                    aria-current={activeTopic?.id === topic.id ? "page" : undefined}
                    {...linkProps({ kind: "topic", topicId: topic.id })}
                  >
                    {topic.label}
                  </a>
                </li>
              ))}
            </ul>
          )}
        </div>
      </nav>
    </div>
  );
}

function FeedSkeleton() {
  return (
    <div className="discover__skeleton" aria-hidden="true">
      <div className="skel skel--lead">
        <div className="skel__text">
          <span className="skel__line skel__line--xl" />
          <span className="skel__line skel__line--xl" />
          <span className="skel__line" />
          <span className="skel__line" />
        </div>
        <span className="skel__media" />
      </div>
      <div className="skel__row">
        {[0, 1, 2].map((index) => (
          <div className="skel skel--card" key={index}>
            <span className="skel__media" />
            <span className="skel__line" />
            <span className="skel__line skel__line--short" />
          </div>
        ))}
      </div>
    </div>
  );
}

function FeedError({ locale, onRetry }: { locale: LocaleCode; onRetry: () => void }) {
  return (
    <div className="discover__error" role="alert">
      <p>{t(locale, "discover.error")}</p>
      <button type="button" className="button button--secondary" onClick={onRetry}>
        {t(locale, "discover.retry")}
      </button>
    </div>
  );
}
