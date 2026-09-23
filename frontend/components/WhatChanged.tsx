import Link from "next/link";

import type { Story } from "@/lib/api";
import { formatCoverage, formatRelativeTime, t, type LocaleCode } from "@/lib/i18n";

export interface TopicChange {
  topicId: string;
  label: string;
  story: Story;
}

/**
 * Audit §25: what changed, across the topics this reader follows.
 *
 * The desk was a list of topics you could go and read. This is the first
 * thing on it that answers a question - "what has moved since I last looked"
 * - which is the difference §23 and §27 are asking for between a workspace
 * and a page of links.
 *
 * "Changed" is meant literally: for each topic, the story cluster whose
 * coverage was most recently added to, tie-broken by how many publishers are
 * carrying it. Both numbers are real columns on the cluster
 * (`last_seen_at`, `source_count`), not a judgement this component makes.
 *
 * §25 asks for varied hierarchy, so the first entry is set as a lead and the
 * rest as rows: on a desk ordered by the reader's own priority, the topic
 * they put first is the one whose news should be biggest.
 */
export function WhatChanged({
  changes,
  locale,
}: {
  changes: TopicChange[];
  locale: LocaleCode;
}) {
  if (changes.length === 0) {
    return <p className="empty-note">{t(locale, "desk.whatChanged.empty")}</p>;
  }

  return (
    <ul className="changed">
      {changes.map((change, index) => (
        <li
          className={`changed__item${index === 0 ? " changed__item--lead" : ""}`}
          key={change.topicId}
        >
          {/* The topic is the organising principle (§27), so it labels the
              entry rather than trailing it as metadata. */}
          <p className="changed__topic">
            <Link href={`/${locale}/desk/${encodeURIComponent(change.topicId)}`}>
              {change.label}
            </Link>
          </p>
          <p className="changed__headline">
            <Link href={`/${locale}/story/${change.story.id}`}>{change.story.title}</Link>
          </p>
          <p className="changed__meta">
            <span>
              {formatCoverage(locale, change.story.source_count, change.story.language_count)}
            </span>
            <time dateTime={change.story.last_seen_at}>
              {t(locale, "desk.whatChanged.updated", {
                time: formatRelativeTime(change.story.last_seen_at, locale),
              })}
            </time>
          </p>
        </li>
      ))}
    </ul>
  );
}
