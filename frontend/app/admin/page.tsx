import Link from "next/link";

import { getAnalyticsOverview } from "@/lib/api";
import { requireAdmin } from "@/lib/adminGuard";

export default async function AdminOverviewPage() {
  const access = await requireAdmin();
  if (!access.ok) return access.element;

  const overview = await getAnalyticsOverview(access.auth);

  return (
    <>
      <h1 style={{ fontFamily: "var(--font-display)", fontSize: "1.4rem" }}>Overview</h1>
      <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
        Since {overview ? new Date(overview.since).toLocaleString("en") : "—"} (last 7 days).
      </p>

      <div className="admin-cards">
        <div className="admin-card">
          <b>{overview?.active_users ?? "—"}</b>
          <span>active readers</span>
        </div>
        <div className="admin-card">
          <b>{overview?.top_articles.length ?? "—"}</b>
          <span>articles with impressions</span>
        </div>
        <div className="admin-card">
          <b>{overview?.top_sources.length ?? "—"}</b>
          <span>sources with impressions</span>
        </div>
      </div>

      <p>
        <Link href="/admin/analytics">Full analytics</Link> ·{" "}
        <Link href="/admin/sources">Source health</Link> ·{" "}
        <Link href="/admin/ingest-runs">Ingestion runs</Link> ·{" "}
        <Link href="/admin/articles">Moderation</Link> ·{" "}
        <Link href="/admin/users">Users</Link> · <Link href="/admin/invites">Invites</Link> ·{" "}
        <Link href="/admin/audit-log">Audit log</Link>
      </p>
    </>
  );
}
