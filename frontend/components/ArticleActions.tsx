"use client";

import { useState, useTransition } from "react";

import {
  notInterestedAction,
  saveArticleAction,
  shareArticleAction,
  undoNotInterestedAction,
  unsaveArticleAction,
} from "@/lib/actions";
import { t, type LocaleCode } from "@/lib/i18n";

type Outcome = null | "hidden" | "hide-failed" | "save-failed" | "undo-failed" | "share-failed";

export function ArticleActions({
  articleId,
  locale,
  surface,
  topicId,
  saved,
  revalidatePath,
  onHidden,
  onRestored,
}: {
  articleId: number;
  locale: LocaleCode;
  surface: "feed" | "explore" | "search" | "topic" | "onboarding";
  /** Only ever set on surface="onboarding" - see ArticleCard's own note on
   * this same field. */
  topicId?: string;
  saved: boolean;
  revalidatePath: string;
  /** Told once "Not interested" succeeds, so the card that owns this control
   * can step its own content back rather than the confirmation being the
   * only thing that changed. */
  onHidden?: () => void;
  /** Told once undo succeeds, so the card can un-dim. */
  onRestored?: () => void;
}) {
  const [isPending, startTransition] = useTransition();
  const [outcome, setOutcome] = useState<Outcome>(null);
  const [shared, setShared] = useState(false);

  /**
   * Once the signal is sent, the controls go and a status line - now with a
   * real undo beside it - takes their place. Before, "Not interested"
   * reported nothing at all: the button re-enabled and the card sat there
   * unchanged, so the reader had no way to know whether they had just taught
   * the ranker something or clicked into a void.
   *
   * The undo is persistent, not time-boxed: it stays available for as long
   * as the card does, rather than auto-expiring on a timer a reader has to
   * notice and beat. It is a real DELETE against the signal already logged
   * (`DELETE /v1/not-interested/{id}`), not a client-side illusion that
   * quietly leaves the original mark standing - see that endpoint's own
   * docstring for how the log stays append-only either way.
   */
  if (outcome === "hidden" || outcome === "undo-failed") {
    return (
      <div className="card__actions">
        <p className="card__status" role="status">
          {t(locale, "actions.notInterested.done")}
        </p>
        <button
          type="button"
          className="card__action"
          disabled={isPending}
          onClick={() =>
            startTransition(async () => {
              const ok = await undoNotInterestedAction(articleId, surface, revalidatePath);
              if (ok) {
                setOutcome(null);
                onRestored?.();
              } else {
                setOutcome("undo-failed");
              }
            })
          }
        >
          {t(locale, "actions.undo")}
        </button>
        {outcome === "undo-failed" && (
          <p className="card__status card__status--error" role="alert">
            {t(locale, "actions.undo.failed")}
          </p>
        )}
      </div>
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
      <button
        type="button"
        className="card__action"
        disabled={isPending}
        onClick={() =>
          startTransition(async () => {
            setOutcome(null);
            const ok = await shareArticleAction(articleId, surface, topicId);
            if (ok) {
              setShared(true);
            } else {
              setOutcome("share-failed");
            }
          })
        }
      >
        {t(locale, shared ? "actions.share.done" : "actions.share")}
      </button>
      {outcome && (
        <p className="card__status card__status--error" role="alert">
          {t(
            locale,
            outcome === "save-failed"
              ? "actions.save.failed"
              : outcome === "share-failed"
                ? "actions.share.failed"
                : "actions.notInterested.failed",
          )}
        </p>
      )}
    </div>
  );
}
