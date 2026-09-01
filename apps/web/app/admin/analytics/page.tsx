import { getAnalyticsOverview } from "@/lib/api";
import { requireAdmin } from "@/lib/adminGuard";

export const metadata = { title: "Analytics · Admin" };

export default async function AdminAnalyticsPage() {
  const access = await requireAdmin();
  if (!access.ok) return access.element;

  const overview = await getAnalyticsOverview(access.auth);

  return (
    <>
      <h1 style={{ fontFamily: "var(--font-display)", fontSize: "1.4rem" }}>Analytics</h1>
      <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
        Last 7 days, since {overview ? new Date(overview.since).toLocaleString("en") : "—"}. Dwell
        time and scroll depth are not shown yet - nothing on the site reports them.
      </p>

      <h2 style={{ fontFamily: "var(--font-display)", fontSize: "1.1rem" }}>
        Experiment: heuristic ranker vs chronological
      </h2>
      <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
        Stage 5&rsquo;s A/B split. Every reader is bucketed once, deterministically, by their own
        id - this is CTR for each bucket over the same window above.
      </p>
      <div className="admin-table-wrap">
        <table className="admin-table">
          <thead>
            <tr>
              <th>Policy</th>
              <th>Impressions</th>
              <th>Clicks</th>
              <th>CTR</th>
            </tr>
          </thead>
          <tbody>
            {overview?.ctr_by_ranking_policy.map((row) => (
              <tr key={row.ranking_policy}>
                <td>{row.ranking_policy}</td>
                <td>{row.impressions}</td>
                <td>{row.clicks}</td>
                <td>
                  {row.impressions > 0
                    ? `${((row.clicks / row.impressions) * 100).toFixed(1)}%`
                    : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h2 style={{ fontFamily: "var(--font-display)", fontSize: "1.1rem" }}>CTR by surface</h2>
      <div className="admin-table-wrap">
        <table className="admin-table">
          <thead>
            <tr>
              <th>Surface</th>
              <th>Impressions</th>
              <th>Clicks</th>
              <th>CTR</th>
            </tr>
          </thead>
          <tbody>
            {overview?.ctr_by_surface.map((row) => (
              <tr key={row.surface}>
                <td>{row.surface}</td>
                <td>{row.impressions}</td>
                <td>{row.clicks}</td>
                <td>
                  {row.impressions > 0
                    ? `${((row.clicks / row.impressions) * 100).toFixed(1)}%`
                    : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h2 style={{ fontFamily: "var(--font-display)", fontSize: "1.1rem" }}>Top articles</h2>
      <div className="admin-table-wrap">
        <table className="admin-table">
          <thead>
            <tr>
              <th>Title</th>
              <th>Language</th>
              <th>Impressions</th>
            </tr>
          </thead>
          <tbody>
            {overview?.top_articles.map((row) => (
              <tr key={row.id}>
                <td style={{ whiteSpace: "normal", maxWidth: "28rem" }}>{row.title}</td>
                <td>{row.language}</td>
                <td>{row.impressions}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h2 style={{ fontFamily: "var(--font-display)", fontSize: "1.1rem" }}>Top sources</h2>
      <div className="admin-table-wrap">
        <table className="admin-table">
          <thead>
            <tr>
              <th>Source</th>
              <th>Impressions</th>
            </tr>
          </thead>
          <tbody>
            {overview?.top_sources.map((row) => (
              <tr key={row.id}>
                <td>{row.name}</td>
                <td>{row.impressions}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
