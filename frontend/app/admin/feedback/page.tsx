import { getAdminFeedback } from "@/lib/api";
import { requireAdmin } from "@/lib/adminGuard";

export const metadata = { title: "Feedback · Admin" };

export default async function AdminFeedbackPage() {
  const access = await requireAdmin();
  if (!access.ok) return access.element;

  const entries = await getAdminFeedback(access.auth);

  return (
    <>
      <h1 style={{ fontFamily: "var(--font-display)", fontSize: "1.4rem" }}>Feedback</h1>
      <div className="admin-table-wrap">
        <table className="admin-table">
          <thead>
            <tr>
              <th>When</th>
              <th>User</th>
              <th>Locale</th>
              <th>Page</th>
              <th>Message</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((entry) => (
              <tr key={entry.id}>
                <td>{new Date(entry.created_at).toLocaleString("en")}</td>
                <td style={{ fontFamily: "monospace", fontSize: "0.78rem" }}>
                  {entry.user_id ? entry.user_id.slice(0, 8) : "—"}
                </td>
                <td>{entry.locale}</td>
                <td>{entry.path ?? "—"}</td>
                <td style={{ whiteSpace: "normal", maxWidth: "28rem" }}>{entry.message}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {entries.length === 0 && <p className="empty">No feedback yet.</p>}
    </>
  );
}
