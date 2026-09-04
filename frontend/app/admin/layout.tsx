import "@/app/globals.css";

import Link from "next/link";
import type { ReactNode } from "react";

export const metadata = { title: "Admin · JustNews" };

const NAV = [
  { href: "/admin", label: "Overview" },
  { href: "/admin/sources", label: "Sources" },
  { href: "/admin/ingest-runs", label: "Ingest runs" },
  { href: "/admin/articles", label: "Moderation" },
  { href: "/admin/taxonomy", label: "Taxonomy" },
  { href: "/admin/users", label: "Users" },
  { href: "/admin/analytics", label: "Analytics" },
  { href: "/admin/invites", label: "Invites" },
  { href: "/admin/feedback", label: "Feedback" },
  { href: "/admin/audit-log", label: "Audit log" },
];

export default function AdminLayout({ children }: { children: ReactNode }) {
  // English-only, no locale routing - an internal tool, not a reader-facing
  // surface. Its own <html>/<body>: this branch of the route tree never
  // passes through [locale]/layout.tsx, which is the only other place they
  // are defined.
  return (
    <html lang="en">
      <body>
        <div className="admin-shell">
          <header className="admin-header">
            <span className="wordmark">JustNews admin</span>
            <Link href="/en" style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
              Back to the site
            </Link>
          </header>
          <nav aria-label="Admin">
            <ul className="admin-nav">
              {NAV.map((item) => (
                <li key={item.href}>
                  <Link href={item.href}>{item.label}</Link>
                </li>
              ))}
            </ul>
          </nav>
          <main>{children}</main>
        </div>
      </body>
    </html>
  );
}
