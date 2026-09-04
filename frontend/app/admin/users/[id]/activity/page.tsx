import { getUserActivity } from "@/lib/api";
import { requireAdmin } from "@/lib/adminGuard";

export const metadata = { title: "User activity · Admin" };

export default async function AdminUserActivityPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const access = await requireAdmin();
  if (!access.ok) return access.element;

  const { id } = await params;
  const entries = await getUserActivity(access.auth, id);

  return (
    <>
      <h1 style={{ fontFamily: "var(--font-display)", fontSize: "1.4rem" }}>
        Activity — <code>{id}</code>
      </h1>
      <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
        Every impression and interaction this reader has, merged and ordered most recent
        first. Not a session replay - only what this system already logs for the Stage 6
        offline evaluators.
      </p>
      <div className="admin-table-wrap">
        <table className="admin-table">
          <thead>
            <tr>
              <th>When</th>
              <th>Kind</th>
              <th>Article</th>
              <th>Surface</th>
              <th>Detail</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((entry, index) => (
              <tr key={`${entry.kind}-${entry.article_id}-${entry.occurred_at}-${index}`}>
                <td>{new Date(entry.occurred_at).toLocaleString("en")}</td>
                <td>
                  <span className={`pill ${entry.kind === "impression" ? "pill--ok" : "pill--warn"}`}>
                    {entry.kind}
                  </span>
                </td>
                <td style={{ whiteSpace: "normal", maxWidth: "22rem" }}>{entry.article_title}</td>
                <td>{entry.surface}</td>
                <td>
                  {entry.kind === "impression"
                    ? `policy: ${entry.ranking_policy}, position: ${entry.position}`
                    : entry.event_type}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {entries.length === 0 && <p className="empty">No activity logged for this reader yet.</p>}
    </>
  );
}
