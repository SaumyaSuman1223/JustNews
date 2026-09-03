"use client";

import { useTransition } from "react";

import { followSourceAction, unfollowSourceAction } from "@/lib/actions";

/**
 * Google News calls this a Preferred Source. Follows have only ever covered
 * topics here, so a reader who trusts one publisher over another had no way
 * to say so.
 *
 * `aria-pressed` rather than swapping the label alone: the control is a
 * toggle, and a screen reader should hear its state, not infer it from a
 * verb. Same pattern the save button already uses.
 */
export function FollowSourceButton({
  sourceId,
  sourceName,
  following,
  revalidatePath,
}: {
  sourceId: number;
  sourceName: string;
  following: boolean;
  revalidatePath: string;
}) {
  const [pending, startTransition] = useTransition();

  return (
    <button
      type="button"
      className="card__action"
      aria-pressed={following}
      disabled={pending}
      onClick={() =>
        startTransition(async () => {
          await (following
            ? unfollowSourceAction(sourceId, revalidatePath)
            : followSourceAction(sourceId, revalidatePath));
        })
      }
    >
      {following ? `Following ${sourceName}` : `Follow ${sourceName}`}
    </button>
  );
}
