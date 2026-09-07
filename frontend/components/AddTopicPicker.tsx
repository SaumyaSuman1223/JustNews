"use client";

import { useState } from "react";

import { FollowTopicChip } from "@/components/FollowTopicChip";
import type { Topic } from "@/lib/api";
import { t, type LocaleCode } from "@/lib/i18n";

/**
 * "+ Add Topic": reveals the topic catalogue as a picker.
 *
 * `topics` arrives already carrying curated labels (see
 * `lib/curatedTopics.ts`, applied once by the caller) - §24's "I care about
 * AI", not the raw IPTC string underneath it. Every chip already knows
 * whether the reader follows it - `FollowTopicChip` is the same toggle the
 * old topic-browse page used, so tapping one here and tapping one there
 * write the identical UserFollow row.
 */
export function AddTopicPicker({
  topics,
  followedIds,
  locale,
  revalidatePath,
}: {
  topics: Topic[];
  followedIds: Set<string>;
  locale: LocaleCode;
  revalidatePath: string;
}) {
  const [open, setOpen] = useState(false);

  return (
    <div className="desk-add">
      <button type="button" className="button button--secondary" onClick={() => setOpen((v) => !v)}>
        {t(locale, open ? "desk.addTopic.done" : "desk.addTopic")}
      </button>
      {open && (
        <ul className="chip-list topic-picker">
          {topics.map((topic) => (
            <li key={topic.id}>
              <FollowTopicChip
                topicId={topic.id}
                label={topic.label}
                locale={locale}
                following={followedIds.has(topic.id)}
                revalidatePath={revalidatePath}
                className="topic-chip"
              />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
