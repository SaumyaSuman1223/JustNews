import { getAuditLog } from "@/lib/api";
import { requireAdmin } from "@/lib/adminGuard";

export const metadata = { title: "Audit log · Admin" };

export default async function AdminAuditLogPage() {
  const access = await requireAdmin();
  if (!access.ok) return access.element;

  const entries = await getAuditLog(access.auth);

  return (
    <>
      <h1 style={{ fontFamily: "var(--font-display)", fontSize: "1.4rem" }}>Audit log</h1>
      <div className="admin-table-wrap">
        <table className="admin-table">
          <thead>
            <tr>
              <th>When</th>
              <th>Admin</th>
              <th>Action</th>
              <th>Target</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((entry) => (
              <tr key={entry.id}>
                <td>{new Date(entry.created_at).toLocaleString("en")}</td>
                <td style={{ fontFamily: "monospace", fontSize: "0.78rem" }}>
                  {entry.admin_user_id.slice(0, 8)}
                </td>
                <td>{entry.action}</td>
                <td>
                  {entry.target_type ? `${entry.target_type}:${entry.target_id}` : "—"}
                </td>
                <td style={{ whiteSpace: "normal", maxWidth: "20rem" }}>
                  {entry.details ? JSON.stringify(entry.details) : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {entries.length === 0 && <p className="empty">No admin actions yet.</p>}
    </>
  );
}
