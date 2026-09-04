import Link from "next/link";

import type { Story } from "@/lib/api";
import { formatRelativeTime, type LocaleCode, t } from "@/lib/i18n";

/**
 * A topic's story clusters, plotted by when each one broke.
 *
 * Static, deliberately: the frontend spec calls out "avoid animated
 * timelines that constantly move" - this renders once, from
 * `StoryCluster.first_seen_at`/`last_seen_at`, real dates rather than an
 * invented per-day rollup.
 */
export function Timeline({
  stories,
  locale,
  topicHref,
}: {
  stories: Story[];
  locale: LocaleCode;
  topicHref: (storyId: number) => string;
}) {
  if (stories.length === 0) {
    return <p className="notice">{t(locale, "desk.timeline.empty")}</p>;
  }

  return (
    <ol className="timeline">
      {stories.map((story) => (
        <li className="timeline__item" key={story.id}>
          <span className="timeline__dot" aria-hidden="true" />
          <div className="timeline__body">
            <p className="timeline__date">{formatRelativeTime(story.first_seen_at, locale)}</p>
            <p className="timeline__title">
              <Link href={topicHref(story.id)}>{story.title}</Link>
            </p>
            <p className="timeline__meta">
              {t(locale, "desk.timeline.coverage", {
                sources: story.source_count,
                languages: story.language_count,
              })}
            </p>
          </div>
        </li>
      ))}
    </ol>
  );
}
