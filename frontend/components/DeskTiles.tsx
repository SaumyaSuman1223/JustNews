"use client";

import Link from "next/link";
import { useState, useTransition } from "react";

import { reorderFollowsAction, unfollowTopicAction } from "@/lib/actions";
import { t, type LocaleCode } from "@/lib/i18n";

export interface DeskTile {
  topicId: string;
  label: string;
  /** Live article count for this topic - the same figure the topic's own
   * Overview panel shows, not a fabricated "story count". */
  articleCount: number;
}

/**
 * My Desk's followed-topic tiles: add, remove, reorder.
 *
 * Reorder is a pair of buttons, not drag-and-drop - the frontend spec asks
 * for reordering, not for a gesture, and a keyboard-operable up/down pair
 * needs no new dependency (CLAUDE.md: no dependency without naming what it
 * replaces). Each move is optimistic locally and then written for real
 * against the reader's whole follow list - `PUT /v1/follows/order` takes
 * the complete order, not a single swap.
 */
export function DeskTiles({
  tiles,
  locale,
  revalidatePath,
}: {
  tiles: DeskTile[];
  locale: LocaleCode;
  revalidatePath: string;
}) {
  const [order, setOrder] = useState(tiles);
  const [pending, startTransition] = useTransition();
  const [failed, setFailed] = useState(false);

  function move(index: number, delta: -1 | 1) {
    const target = index + delta;
    if (target < 0 || target >= order.length) return;
    const next = order.slice();
    const moved = next[index];
    const displaced = next[target];
    if (!moved || !displaced) return;
    next[index] = displaced;
    next[target] = moved;
    setOrder(next);
    startTransition(async () => {
      const ok = await reorderFollowsAction(
        next.map((tile) => tile.topicId),
        revalidatePath,
      );
      setFailed(!ok);
    });
  }

  function remove(topicId: string) {
    setOrder((current) => current.filter((tile) => tile.topicId !== topicId));
    startTransition(async () => {
      const ok = await unfollowTopicAction(topicId, revalidatePath);
      if (!ok) setFailed(true);
    });
  }

  return (
    <>
      <ul className="desk-tiles">
        {order.map((tile, index) => (
          <li className="desk-tile" key={tile.topicId}>
            <Link className="desk-tile__link" href={`/${locale}/desk/${encodeURIComponent(tile.topicId)}`}>
              <span className="desk-tile__label">{tile.label}</span>
              <span className="desk-tile__count">
                {tile.articleCount.toLocaleString(locale)} {t(locale, "stats.articles")}
              </span>
            </Link>
            <div className="desk-tile__controls">
              <button
                type="button"
                disabled={pending || index === 0}
                aria-label={t(locale, "desk.moveUp")}
                onClick={() => move(index, -1)}
              >
                ↑
              </button>
              <button
                type="button"
                disabled={pending || index === order.length - 1}
                aria-label={t(locale, "desk.moveDown")}
                onClick={() => move(index, 1)}
              >
                ↓
              </button>
              <button
                type="button"
                className="desk-tile__remove"
                disabled={pending}
                onClick={() => remove(tile.topicId)}
              >
                {t(locale, "desk.remove")}
              </button>
            </div>
          </li>
        ))}
      </ul>
      {failed && (
        <p className="form-error" role="alert">
          {t(locale, "desk.actionFailed")}
        </p>
      )}
    </>
  );
}
