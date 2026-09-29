"use client";

import type { ReactNode } from "react";

/**
 * Submits the surrounding form as soon as a choice inside it changes - a
 * preference applies when it is picked, as a settings screen's does. The
 * form keeps its own submit button in a <noscript>, so it still works
 * without JavaScript.
 */
export function SubmitOnChange({ children }: { children: ReactNode }) {
  return (
    <div
      className="submit-on-change"
      onChange={(event) => event.currentTarget.closest("form")?.requestSubmit()}
    >
      {children}
    </div>
  );
}
