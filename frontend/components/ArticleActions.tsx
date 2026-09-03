"use client";

import { useState, useTransition } from "react";

import { notInterestedAction, saveArticleAction, unsaveArticleAction } from "@/lib/actions";
import { t, type LocaleCode } from "@/lib/i18n";

type Outcome = null | "hidden" | "hide-failed" | "save-failed";

export function ArticleActions({
  articleId,
  locale,
  surface,
  saved,
  revalidatePath,
  onHidden,
}: {
  articleId: number;
  locale: LocaleCode;
  surface: "feed" | "explore" | "search" | "topic";
  saved: boolean;
  revalidatePath: string;
  /** Told once "Not interested" succeeds, so the card that owns this control
   * can step its own content back rather than the confirmation being the
   * only thing that changed. */
  onHidden?: () => void;
}) {
  const [isPending, startTransition] = useTransition();
  const [outcome, setOutcome] = useState<Outcome>(null);

  /**
   * Once the signal is sent, the controls go and a status line takes their
   * place. Before, "Not interested" reported nothing at all: the button
   * re-enabled and the card sat there unchanged, so the reader had no way to
   * know whether they had just taught the ranker something or clicked into a
   * void - and pressing it again was the natural response.
   *
   * This is deliberately not an undo. `/v1/not-interested` is POST-only, so
   * there is nothing to call, and a control that said "undo" while leaving
   * the signal in the log would be a lie about what the product did with it.
   * Real undo needs a DELETE on that route.
   */
  if (outcome === "hidden") {
    return (
      <p className="card__status" role="status">
        {t(locale, "actions.notInterested.done")}
      </p>
    );
  }

  return (
    <div className="card__actions">
      <button
        type="button"
        className="card__action"
        aria-pressed={saved}
        disabled={isPending}
        onClick={() =>
          startTransition(async () => {
            setOutcome(null);
            const ok = saved
              ? await unsaveArticleAction(articleId, revalidatePath)
              : await saveArticleAction(articleId, revalidatePath);
            if (!ok) setOutcome("save-failed");
          })
        }
      >
        {t(locale, saved ? "actions.saved" : "actions.save")}
      </button>
      <button
        type="button"
        className="card__action"
        disabled={isPending}
        onClick={() =>
          startTransition(async () => {
            setOutcome(null);
            const ok = await notInterestedAction(articleId, surface, revalidatePath);
            setOutcome(ok ? "hidden" : "hide-failed");
            if (ok) onHidden?.();
          })
        }
      >
        {t(locale, "actions.notInterested")}
      </button>
      {outcome && (
        <p className="card__status card__status--error" role="alert">
          {t(
            locale,
            outcome === "save-failed" ? "actions.save.failed" : "actions.notInterested.failed",
          )}
        </p>
      )}
    </div>
  );
}
