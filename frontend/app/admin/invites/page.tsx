import { getInvites } from "@/lib/api";
import { requireAdmin } from "@/lib/adminGuard";
import { createInviteAction } from "@/lib/adminActions";

export const metadata = { title: "Invites · Admin" };

export default async function AdminInvitesPage() {
  const access = await requireAdmin();
  if (!access.ok) return access.element;

  const invites = await getInvites(access.auth);

  return (
    <>
      <h1 style={{ fontFamily: "var(--font-display)", fontSize: "1.4rem" }}>Beta invites</h1>

      <form action={createInviteAction} className="inline-form">
        <input type="text" name="note" placeholder="Note (e.g. batch 1)" />
        <input type="number" name="maxUses" defaultValue={1} min={1} max={10000} required />
        <button type="submit" className="button button--secondary">
          Create code
        </button>
      </form>

      <div className="admin-table-wrap">
        <table className="admin-table">
          <thead>
            <tr>
              <th>Code</th>
              <th>Note</th>
              <th>Uses</th>
              <th>Expires</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {invites.map((invite) => (
              <tr key={invite.code}>
                <td style={{ fontFamily: "monospace" }}>{invite.code}</td>
                <td>{invite.note || "—"}</td>
                <td>
                  {invite.uses} / {invite.max_uses}
                </td>
                <td>{invite.expires_at ? new Date(invite.expires_at).toLocaleDateString("en") : "never"}</td>
                <td>{new Date(invite.created_at).toLocaleDateString("en")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {invites.length === 0 && <p className="empty">No invite codes yet.</p>}
    </>
  );
}
