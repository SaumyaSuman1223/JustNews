"use client";

import { useTransition } from "react";

import { notInterestedAction, saveArticleAction, unsaveArticleAction } from "@/lib/actions";

export function ArticleActions({
  articleId,
  surface,
  saved,
  revalidatePath,
}: {
  articleId: number;
  surface: "feed" | "explore" | "search" | "topic";
  saved: boolean;
  revalidatePath: string;
}) {
  const [isPending, startTransition] = useTransition();

  return (
    <div className="card__actions">
      <button
        type="button"
        className="card__action"
        aria-pressed={saved}
        disabled={isPending}
        onClick={() =>
          startTransition(async () => {
            if (saved) await unsaveArticleAction(articleId, revalidatePath);
            else await saveArticleAction(articleId, revalidatePath);
          })
        }
      >
        {saved ? "Saved" : "Save"}
      </button>
      <button
        type="button"
        className="card__action"
        disabled={isPending}
        onClick={() => startTransition(() => notInterestedAction(articleId, surface, revalidatePath))}
      >
        Not interested
      </button>
    </div>
  );
}
