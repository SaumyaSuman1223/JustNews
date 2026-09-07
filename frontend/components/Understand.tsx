import Link from "next/link";

import { Perspectives } from "@/components/Perspectives";
import { Timeline } from "@/components/Timeline";
import type { PerspectiveGroup, Story } from "@/lib/api";
import { formatCoverage, t, type LocaleCode } from "@/lib/i18n";

/** §26's "5 important developments". Breadth of coverage, not recency. */
const KEY_DEVELOPMENTS = 5;

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
 */
export function Understand({
  topicLabel,
  stories,
  perspectives,
  locale,
  storyHref,
}: {
  topicLabel: string;
  stories: Story[];
  perspectives: PerspectiveGroup[];
  locale: LocaleCode;
  storyHref: (storyId: number) => string;
}) {
  // The same fetch, read two ways: by breadth for "what's happening", by date
  // for "what's changing". One request, two questions - which is why the tabs
  // that used to split them were never buying anything.
  const byBreadth = stories
    .slice()
    .sort((a, b) => b.source_count - a.source_count || b.article_count - a.article_count)
    .slice(0, KEY_DEVELOPMENTS);

  return (
    <div className="understand">
      <h2 className="understand__title">
        {t(locale, "desk.understand.heading", { topic: topicLabel })}
      </h2>

      <Module
        heading={t(locale, "desk.understand.happening")}
        note={t(locale, "desk.understand.happening.note")}
      >
        {byBreadth.length === 0 ? (
          <p className="notice">{t(locale, "desk.keyDevelopments.empty")}</p>
        ) : (
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
        )}
      </Module>

      <Module
        heading={t(locale, "desk.understand.saying")}
        note={t(locale, "desk.understand.saying.note")}
      >
        <Perspectives groups={perspectives} locale={locale} headingLevel={3} />
      </Module>

      <Module
        heading={t(locale, "desk.understand.changing")}
        note={t(locale, "desk.understand.changing.note")}
      >
        <Timeline stories={stories} locale={locale} topicHref={storyHref} />
      </Module>
    </div>
  );
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
