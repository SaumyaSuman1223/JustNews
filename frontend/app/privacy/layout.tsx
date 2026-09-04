import "@/app/globals.css";

import type { ReactNode } from "react";

import { fontVariables } from "@/lib/fonts";

export const metadata = { title: "Privacy Policy · JustNews" };

export default function PrivacyLayout({ children }: { children: ReactNode }) {
  // Its own <html>/<body> - this route never passes through
  // [locale]/layout.tsx, the only other place they are defined.
  return (
    <html lang="en" className={fontVariables}>
      <body>
        <div className="shell" style={{ maxWidth: "42rem" }}>
          <main id="main" style={{ paddingBlockStart: "var(--space-8)" }}>
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
