"use client";

import { useState, useTransition } from "react";

import { followSourceAction, unfollowSourceAction } from "@/lib/actions";
import { t, type LocaleCode } from "@/lib/i18n";

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
  locale,
  following,
  revalidatePath,
}: {
  sourceId: number;
  sourceName: string;
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
        className="card__action"
        aria-pressed={following}
        disabled={pending}
        onClick={() =>
          startTransition(async () => {
            setFailed(false);
            const ok = await (following
              ? unfollowSourceAction(sourceId, revalidatePath)
              : followSourceAction(sourceId, revalidatePath));
            if (!ok) setFailed(true);
          })
        }
      >
        {t(locale, following ? "actions.following" : "actions.follow", { source: sourceName })}
      </button>
      {failed && (
        <p className="card__status card__status--error" role="alert">
          {t(locale, "actions.follow.failed")}
        </p>
      )}
    </>
  );
}
