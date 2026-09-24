import Link from "next/link";

import { Perspectives } from "@/components/Perspectives";
import { Timeline } from "@/components/Timeline";
import type { Article, PerspectiveGroup, Story } from "@/lib/api";
import { formatCoverage, formatRelativeTime, t, tPlural, type LocaleCode } from "@/lib/i18n";

/** §26's "5 important developments". Breadth of coverage, not recency. */
const KEY_DEVELOPMENTS = 5;
/** How many recent reports stand in when there are no developments yet. */
const LATEST_FALLBACK = 6;
/** How many outlets the fallback tally names. */
const OUTLET_TALLY = 6;

/**
 * Audit §26: understand the topic.
 *
 * Three modules on one page rather than three tabs to hunt through - "what's
 * happening", "who is saying what", "what's changing". They used to be tabs,
 * which meant a reader had to already know what they were looking for to find
 * any of it, and that is precisely the difference §27 draws between an
 * information workspace and another page showing news.
 *
 * Every module is built from data that already exists. There is no Analysis
 * here and nothing inferred: §26 explicitly says not to implement the future
 * analysis system prematurely, and the honest version of "understand" is a
 * better arrangement of facts we can point at.
 *
 * Fifth-pass §2.1: the three modules are built on story clusters, and a topic
 * can have plenty of reporting and no clusters at all (Politics had 69
 * articles and zero stories the first time this was run against real data).
 * Three empty boxes told the reader the topic had nothing. When there are no
 * stories, `latest` - the topic's own recent articles - stands in: the
 * reporting itself under "what's happening", and a tally of which outlets
 * filed it under "who is saying what". Both are plain counts of real rows,
 * and each module says plainly that it is showing reporting, not stories.
 */
export function Understand({
  topicLabel,
  stories,
  perspectives,
  latest = [],
  locale,
  storyHref,
}: {
  topicLabel: string;
  stories: Story[];
  perspectives: PerspectiveGroup[];
  latest?: Article[];
  locale: LocaleCode;
  storyHref: (storyId: number) => string;
}) {
  // The same fetch, read two ways: by breadth for "what's happening", by date
  // for "what's changing". One request, two questions - which is why the tabs
  // that used to split them were never buying anything.
  // A "development the most publishers are covering" needs more than one
  // publisher. A cluster of one outlet's own pieces is real, but it answers a
  // different question, so it does not stand in as a development.
  const multiSource = stories.filter((story) => story.source_count > 1);
  const byBreadth = multiSource
    .slice()
    .sort((a, b) => b.source_count - a.source_count || b.article_count - a.article_count)
    .slice(0, KEY_DEVELOPMENTS);
  const fallback = byBreadth.length === 0 ? latest.slice(0, LATEST_FALLBACK) : [];
  const outlets = perspectives.length === 0 ? tallyOutlets(latest) : [];

  return (
    <div className="understand">
      <h2 className="understand__title">
        {t(locale, "desk.understand.heading", { topic: topicLabel })}
      </h2>

      <Module
        heading={t(locale, "desk.understand.happening")}
        note={t(
          locale,
          fallback.length > 0
            ? "desk.understand.happening.fallbackNote"
            : "desk.understand.happening.note",
        )}
      >
        {byBreadth.length > 0 ? (
          <ol className="understand__developments">
            {byBreadth.map((story, index) => (
              <li key={story.id}>
                {/* The rank is information, not decoration: this list is
                    ordered by how many publishers carried the story, and the
                    number is the only thing that says so. */}
                <span className="understand__rank" aria-hidden="true">
                  {String(index + 1).padStart(2, "0")}
                </span>
                <div>
                  <p className="understand__headline">
                    <Link href={storyHref(story.id)}>{story.title}</Link>
                  </p>
                  <p className="understand__meta">
                    {formatCoverage(locale, story.source_count, story.language_count)}
                  </p>
                </div>
              </li>
            ))}
          </ol>
        ) : fallback.length > 0 ? (
          // Unnumbered on purpose: this list is newest-first, and a rank would
          // claim an ordering by importance that nothing here measured.
          <ul className="understand__latest">
            {fallback.map((article) => (
              <li key={article.id}>
                <p className="understand__headline">
                  <Link href={`/${locale}/a/${article.id}`}>{article.title}</Link>
                </p>
                <p className="understand__meta">
                  {article.source_name} · {formatRelativeTime(article.published_at, locale)}
                </p>
              </li>
            ))}
          </ul>
        ) : (
          <p className="empty-note">{t(locale, "desk.keyDevelopments.empty")}</p>
        )}
      </Module>

      <Module
        heading={t(locale, "desk.understand.saying")}
        note={t(
          locale,
          outlets.length > 0
            ? "desk.understand.saying.fallbackNote"
            : "desk.understand.saying.note",
        )}
      >
        {outlets.length > 0 ? (
          <ul className="understand__outlets">
            {outlets.map((outlet) => (
              <li key={outlet.name}>
                <span className="understand__outlet">{outlet.name}</span>
                <span className="understand__meta">
                  {tPlural(locale, "story.reports", outlet.count)}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <Perspectives groups={perspectives} locale={locale} headingLevel={3} />
        )}
      </Module>

      {/* "What's changing" plots stories over time. With no stories it could
          only restate the reporting list above in date order, so it steps
          aside rather than repeat it or print an empty box. */}
      {multiSource.length > 0 && (
        <Module
          heading={t(locale, "desk.understand.changing")}
          note={t(locale, "desk.understand.changing.note")}
        >
          <Timeline stories={multiSource} locale={locale} topicHref={storyHref} />
        </Module>
      )}
    </div>
  );
}

/** Outlets by how many of these articles each filed, most first. */
function tallyOutlets(articles: Article[]): { name: string; count: number }[] {
  const counts = new Map<string, number>();
  for (const article of articles) {
    counts.set(article.source_name, (counts.get(article.source_name) ?? 0) + 1);
  }
  return [...counts.entries()]
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count || a.name.localeCompare(b.name))
    .slice(0, OUTLET_TALLY);
}

/**
 * §26 draws each module as a heading over a rule with a line of explanation
 * beside it. The rule is the module's own boundary - no card, per §32.
 */
function Module({
  heading,
  note,
  children,
}: {
  heading: string;
  note: string;
  children: React.ReactNode;
}) {
  return (
    <section className="understand__module">
      <h3 className="understand__heading">{heading}</h3>
      <p className="understand__note">{note}</p>
      {children}
    </section>
  );
}
