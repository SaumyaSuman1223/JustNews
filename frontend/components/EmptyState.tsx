import Link from "next/link";
import type { ReactNode } from "react";

export interface EmptyStateProps {
  /** What is not here. One line, in the reader's terms. */
  title: string;
  /** Why, and what it means for them. Optional - some emptiness is obvious. */
  body?: ReactNode;
  /** The single next thing worth doing. An empty state without one is a
   * dead end, which is the whole failure mode this component exists to fix. */
  action?: { href: string; label: string };
}

export function EmptyState({ title, body, action }: EmptyStateProps) {
  return (
    <div className="empty">
      <p className="empty__title">{title}</p>
      {body && <p className="empty__body">{body}</p>}
      {action && (
        <Link className="button button--secondary" href={action.href}>
          {action.label}
        </Link>
      )}
    </div>
  );
}
