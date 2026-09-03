import { getAdminUsers } from "@/lib/api";
import { requireAdmin } from "@/lib/adminGuard";
import { setUserRoleAction } from "@/lib/adminActions";

export const metadata = { title: "Users · Admin" };

export default async function AdminUsersPage() {
  const access = await requireAdmin();
  if (!access.ok) return access.element;

  const users = await getAdminUsers(access.auth);

  return (
    <>
      <h1 style={{ fontFamily: "var(--font-display)", fontSize: "1.4rem" }}>Users</h1>
      <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
        No email is shown - this table never stores one, only Supabase&rsquo;s own auth.users
        does. A reader is identified here by id, role and invite status.
      </p>
      <div className="admin-table-wrap">
        <table className="admin-table">
          <thead>
            <tr>
              <th>Id</th>
              <th>Role</th>
              <th>Invite redeemed</th>
              <th>Languages</th>
              <th>Joined</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.id}>
                <td style={{ fontFamily: "monospace", fontSize: "0.78rem" }}>{user.id}</td>
                <td>
                  <span className={`pill ${user.role === "admin" ? "pill--warn" : "pill--ok"}`}>
                    {user.role}
                  </span>
                </td>
                <td>
                  {user.invite_redeemed_at
                    ? new Date(user.invite_redeemed_at).toLocaleDateString("en")
                    : "—"}
                </td>
                <td>{user.preferred_languages.join(", ") || "—"}</td>
                <td>{new Date(user.created_at).toLocaleDateString("en")}</td>
                <td>
                  <form action={setUserRoleAction} className="inline-form" style={{ margin: 0 }}>
                    <input type="hidden" name="userId" value={user.id} />
                    <input
                      type="hidden"
                      name="role"
                      value={user.role === "admin" ? "reader" : "admin"}
                    />
                    <button type="submit" className="card__action">
                      {user.role === "admin" ? "Demote" : "Promote"}
                    </button>
                  </form>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
