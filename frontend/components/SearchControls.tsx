"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, useSyncExternalStore } from "react";

import type { SourceOption, Topic } from "@/lib/api";
import { curatedTopicLabel } from "@/lib/curatedTopics";
import { viewHref } from "@/lib/discoverView";
import { locales, t, type LocaleCode } from "@/lib/i18n";

/** How many of each kind the type-ahead offers. */
const SUGGESTIONS_PER_KIND = 3;

const RECENT_KEY = "jn_recent_searches";
const RECENT_LIMIT = 5;

/**
 * Recent searches, as an external store rather than component state.
 *
 * `localStorage` is exactly what `useSyncExternalStore` is for: it exists
 * only on the client, so the server snapshot is empty and the client's first
 * paint agrees with the server's HTML instead of hydrating into a mismatch.
 * Reading it into state from an effect would render the list, then re-render
 * with it - a flash, and a lint rule pointing at the flash.
 *
 * The snapshot is cached because React compares snapshots by reference: a
 * fresh array from every `getSnapshot` is a new reference every time, which
 * is an infinite render loop rather than a subtle inefficiency.
 */
const EMPTY: string[] = [];
let cache: string[] | null = null;
const listeners = new Set<() => void>();

function readRecent(): string[] {
  try {
    const stored = window.localStorage.getItem(RECENT_KEY);
    return stored ? (JSON.parse(stored) as string[]).slice(0, RECENT_LIMIT) : EMPTY;
  } catch {
    // A private window, or storage the browser refuses. Recent searches are a
    // convenience; losing them is not worth an error path.
    return EMPTY;
  }
}

function getSnapshot(): string[] {
  if (cache === null) cache = readRecent();
  return cache;
}

/** Empty on the server - there is no per-device history to know about yet. */
function getServerSnapshot(): string[] {
  return EMPTY;
}

function subscribe(onChange: () => void): () => void {
  listeners.add(onChange);
  // Another tab searching should update this one's list.
  window.addEventListener("storage", invalidate);
  return () => {
    listeners.delete(onChange);
    window.removeEventListener("storage", invalidate);
  };
}

function invalidate(): void {
  cache = null;
  for (const listener of listeners) listener();
}

function writeRecent(next: string[]): void {
  try {
    window.localStorage.setItem(RECENT_KEY, JSON.stringify(next));
  } catch {
    /* see readRecent */
  }
  invalidate();
}

/**
 * Search's own input and filters.
 *
 * The masthead already has a search box, but that one is a way *into* this
 * page; §29 asks for a prominent input on the page itself, which is what a
 * reader refining a query actually reaches for. Both submit here.
 *
 * Filters are a GET form, so a filtered search is a URL: shareable, and the
 * back button steps through refinements the way it should. Nothing here holds
 * results in state - the server component renders those from the query
 * string, which is also why changing a filter is a navigation and not a
 * fetch.
 */
export function SearchControls({
  locale,
  query,
  topic,
  language,
  source,
  date,
  topics,
  sources,
}: {
  locale: LocaleCode;
  query: string;
  topic: string;
  language: string;
  source: string;
  date: string;
  topics: Topic[];
  sources: SourceOption[];
}) {
  const router = useRouter();
  const form = useRef<HTMLFormElement>(null);
  // What is in the box right now, for the type-ahead. The input itself stays
  // uncontrolled (defaultValue) so the form still submits without JS.
  const [draft, setDraft] = useState(query);
  const recent = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  // Records the query that actually ran, not what was typed - so a search
  // abandoned mid-word never lands in the list. Writing to storage is a real
  // side effect, which is what an effect is for; the render reads the store.
  useEffect(() => {
    if (query.length < 2) return;
    const current = readRecent();
    if (current[0] === query) return;
    writeRecent([query, ...current.filter((item) => item !== query)].slice(0, RECENT_LIMIT));
  }, [query]);

  // Fifth pass F5: topics and publishers whose name matches what is being
  // typed, as direct links - "politics" goes to the Politics desk rather than
  // to forty articles that mention the word. Matched client-side over the
  // lists this page already loaded for its filters, so typing costs no
  // requests. Plain links under the box rather than an ARIA combobox: a
  // keyboard reader tabs to them, a screen reader hears them as a list.
  const needle = draft.trim().toLocaleLowerCase(locale);
  const topicSuggestions =
    needle.length >= 2
      ? topics
          .map((item) => ({ ...item, label: curatedTopicLabel(item.id, item.label, locale) }))
          .filter((item) => item.label.toLocaleLowerCase(locale).includes(needle))
          .slice(0, SUGGESTIONS_PER_KIND)
      : [];
  const sourceSuggestions =
    needle.length >= 2
      ? sources
          .filter((item) => item.name.toLocaleLowerCase(locale).includes(needle))
          .slice(0, SUGGESTIONS_PER_KIND)
      : [];

  function clearRecent() {
    try {
      window.localStorage.removeItem(RECENT_KEY);
    } catch {
      /* see readRecent */
    }
    invalidate();
  }

  return (
    <div className="search-controls">
      <form ref={form} className="search-form" action={`/${locale}/search`} method="get">
        <label className="visually-hidden" htmlFor="search-q">
          {t(locale, "search.heading")}
        </label>
        <input
          id="search-q"
          className="search-form__input"
          type="search"
          name="q"
          defaultValue={query}
          placeholder={t(locale, "search.placeholder")}
          autoComplete="off"
          onChange={(event) => setDraft(event.target.value)}
        />
        <button className="button" type="submit">
          {t(locale, "search.submit")}
        </button>

        <div className="search-filters">
          <label className="search-filter">
            <span>{t(locale, "search.filter.topic")}</span>
            {/* Submitting on change keeps this a one-step control. Without
                JS the form still works - the reader presses the button. */}
            <select
              name="topic"
              defaultValue={topic}
              onChange={() => form.current?.requestSubmit()}
            >
              <option value="">{t(locale, "search.filter.anyTopic")}</option>
              {topics.map((item) => (
                <option key={item.id} value={item.id}>
                  {curatedTopicLabel(item.id, item.label, locale)}
                </option>
              ))}
            </select>
          </label>

          <label className="search-filter">
            <span>{t(locale, "search.filter.language")}</span>
            <select
              name="lang"
              defaultValue={language}
              onChange={() => form.current?.requestSubmit()}
            >
              <option value="">{t(locale, "search.filter.anyLanguage")}</option>
              {locales.map((item) => (
                <option key={item.code} value={item.code}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>

          <label className="search-filter">
            <span>{t(locale, "search.filter.source")}</span>
            <select
              name="source"
              defaultValue={source}
              onChange={() => form.current?.requestSubmit()}
            >
              <option value="">{t(locale, "search.filter.anySource")}</option>
              {sources.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
          </label>

          <label className="search-filter">
            <span>{t(locale, "search.filter.date")}</span>
            <select name="date" defaultValue={date} onChange={() => form.current?.requestSubmit()}>
              <option value="">{t(locale, "search.filter.anyDate")}</option>
              <option value="day">{t(locale, "search.filter.date.day")}</option>
              <option value="week">{t(locale, "search.filter.date.week")}</option>
              <option value="month">{t(locale, "search.filter.date.month")}</option>
            </select>
          </label>
        </div>
      </form>

      {(topicSuggestions.length > 0 || sourceSuggestions.length > 0) && (
        <nav className="search-suggest" aria-label={t(locale, "search.suggest.label")}>
          <span className="search-suggest__label">{t(locale, "search.suggest.label")}</span>
          <ul>
            {topicSuggestions.map((item) => (
              <li key={item.id}>
                <Link href={viewHref(locale, { kind: "topic", topicId: item.id })}>
                  {item.label}
                  <span className="search-suggest__kind">{t(locale, "search.suggest.topic")}</span>
                </Link>
              </li>
            ))}
            {sourceSuggestions.map((item) => (
              <li key={item.id}>
                <Link href={`/${locale}/source/${encodeURIComponent(item.slug)}`}>
                  {item.name}
                  <span className="search-suggest__kind">{t(locale, "search.suggest.source")}</span>
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      )}

      {recent.length > 0 && (
        <div className="search-recent">
          <h2 className="search-recent__heading">{t(locale, "search.recent")}</h2>
          <ul>
            {recent.map((item) => (
              <li key={item}>
                <button
                  type="button"
                  className="chip"
                  onClick={() => router.push(`/${locale}/search?q=${encodeURIComponent(item)}`)}
                >
                  {item}
                </button>
              </li>
            ))}
          </ul>
          <button type="button" className="search-recent__clear" onClick={clearRecent}>
            {t(locale, "search.recent.clear")}
          </button>
        </div>
      )}
    </div>
  );
}
