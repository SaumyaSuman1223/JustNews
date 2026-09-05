import { getSourceHealth } from "@/lib/api";
import { requireAdmin } from "@/lib/adminGuard";
import { setSourceRoleAction } from "@/lib/adminActions";

export const metadata = { title: "Sources · Admin" };

// ADR 0013: a perspective is a fact about who published, so this is the one
// place that fact gets written. Same seven values the sources.source_role
// CHECK constraint enforces - "wire" included, since assigning it is what
// keeps a wire service out of the perspective groups.
const SOURCE_ROLES = [
  "wire",
  "industry",
  "government",
  "academic",
  "investor",
  "consumer",
  "public",
] as const;

export default async function AdminSourcesPage() {
  const access = await requireAdmin();
  if (!access.ok) return access.element;

  const sources = await getSourceHealth(access.auth);

  return (
    <>
      <h1 style={{ fontFamily: "var(--font-display)", fontSize: "1.4rem" }}>Source health</h1>
      <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
        Perspective role is editorially assigned, never inferred (ADR 0013) - leave it unset
        rather than guess. Unset sources still appear in a story&rsquo;s coverage; they just
        don&rsquo;t contribute to a perspective group.
      </p>
      <div className="admin-table-wrap">
        <table className="admin-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Language</th>
              <th>Status</th>
              <th>Feeds</th>
              <th>Failing feeds</th>
              <th>Last success</th>
              <th>Articles</th>
              <th>Perspective role</th>
            </tr>
          </thead>
          <tbody>
            {sources.map((source) => (
              <tr key={source.id}>
                <td>{source.name}</td>
                <td>{source.language}</td>
                <td>
                  <span className={`pill ${source.active ? "pill--ok" : "pill--warn"}`}>
                    {source.active ? "active" : "inactive"}
                  </span>
                </td>
                <td>{source.feed_count}</td>
                <td>
                  {source.failing_feed_count > 0 ? (
                    <span className="pill pill--warn">{source.failing_feed_count}</span>
                  ) : (
                    0
                  )}
                </td>
                <td>
                  {source.last_success_at
                    ? new Date(source.last_success_at).toLocaleString("en")
                    : "never"}
                </td>
                <td>{source.article_count}</td>
                <td>
                  <form
                    action={setSourceRoleAction}
                    className="inline-form"
                    style={{ margin: 0, display: "flex", gap: "0.5rem", alignItems: "center" }}
                  >
                    <input type="hidden" name="sourceId" value={source.id} />
                    <select name="role" defaultValue={source.source_role ?? ""}>
                      <option value="">Unassigned</option>
                      {SOURCE_ROLES.map((role) => (
                        <option key={role} value={role}>
                          {role}
                        </option>
                      ))}
                    </select>
                    <button type="submit" className="card__action">
                      Save
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
