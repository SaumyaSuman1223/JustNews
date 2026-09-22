"use client";

import { useState, useTransition } from "react";

import { followStoryAction, unfollowStoryAction } from "@/lib/actions";
import { t, type LocaleCode } from "@/lib/i18n";

/**
 * Follow one developing story (fifth pass F2). Same toggle pattern as
 * FollowSourceButton - `aria-pressed`, so a screen reader hears the state
 * rather than inferring it from the verb.
 */
export function FollowStoryButton({
  storyId,
  locale,
  following,
  revalidatePath,
}: {
  storyId: number;
  locale: LocaleCode;
  following: boolean;
  revalidatePath: string;
}) {
  const [pending, startTransition] = useTransition();
  const [failed, setFailed] = useState(false);

  return (
    <>
      <button
        type="button"
        className="button button--secondary"
        aria-pressed={following}
        disabled={pending}
        onClick={() =>
          startTransition(async () => {
            setFailed(false);
            const ok = await (following
              ? unfollowStoryAction(storyId, revalidatePath)
              : followStoryAction(storyId, revalidatePath));
            if (!ok) setFailed(true);
          })
        }
      >
        {t(locale, following ? "story.following" : "story.follow")}
      </button>
      {failed && (
        <p className="card__status card__status--error" role="alert">
          {t(locale, "actions.follow.failed")}
        </p>
      )}
    </>
  );
}
