"use client";

import { useState, useTransition } from "react";

import { followTopicAction, unfollowTopicAction } from "@/lib/actions";
import { t, type LocaleCode } from "@/lib/i18n";

/**
 * A direct, explicit alternative to the exploration deck - for a reader who
 * already knows what they want and would rather tap a category than sample
 * twenty cards. Toggling writes a real UserFollow row immediately (the same
 * table the deck's own engagement bridge writes to), so the two paths feed
 * the Stage 5 ranker's topic-affinity boost identically; neither is more
 * "real" than the other.
 */
export function FollowTopicChip({
  topicId,
  label,
  locale,
  following,
  revalidatePath,
  className = "chip",
}: {
  topicId: string;
  label: string;
  locale: LocaleCode;
  following: boolean;
  revalidatePath: string;
  /** My Desk's topic picker wants the editorial `topic-chip` look (§24: "not
   * SaaS-tag heavy"); onboarding's topic deck keeps the default pill. Same
   * toggle, same aria-pressed contract, different surface. */
  className?: string;
}) {
  const [pending, startTransition] = useTransition();
  const [isFollowing, setIsFollowing] = useState(following);
  const [failed, setFailed] = useState(false);

  return (
    <>
      <button
        type="button"
        className={className}
        aria-pressed={isFollowing}
        data-active={isFollowing || undefined}
        disabled={pending}
        onClick={() =>
          startTransition(async () => {
            setFailed(false);
            const ok = await (isFollowing
              ? unfollowTopicAction(topicId, revalidatePath)
              : followTopicAction(topicId, revalidatePath));
            if (ok) {
              setIsFollowing(!isFollowing);
            } else {
              setFailed(true);
            }
          })
        }
      >
        {label}
      </button>
      {failed && (
        <p className="card__status card__status--error" role="alert">
          {t(locale, "actions.follow.failed")}
        </p>
      )}
    </>
  );
}
