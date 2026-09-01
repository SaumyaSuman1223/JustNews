import { getSourceHealth } from "@/lib/api";
import { requireAdmin } from "@/lib/adminGuard";

export const metadata = { title: "Sources · Admin" };

export default async function AdminSourcesPage() {
  const access = await requireAdmin();
  if (!access.ok) return access.element;

  const sources = await getSourceHealth(access.auth);

  return (
    <>
      <h1 style={{ fontFamily: "var(--font-display)", fontSize: "1.4rem" }}>Source health</h1>
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
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
