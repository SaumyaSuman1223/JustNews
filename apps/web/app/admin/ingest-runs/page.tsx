import { getIngestRuns } from "@/lib/api";
import { requireAdmin } from "@/lib/adminGuard";

export const metadata = { title: "Ingest runs · Admin" };

export default async function AdminIngestRunsPage() {
  const access = await requireAdmin();
  if (!access.ok) return access.element;

  const runs = await getIngestRuns(access.auth);

  return (
    <>
      <h1 style={{ fontFamily: "var(--font-display)", fontSize: "1.4rem" }}>Ingestion runs</h1>
      <div className="admin-table-wrap">
        <table className="admin-table">
          <thead>
            <tr>
              <th>Started</th>
              <th>Trigger</th>
              <th>Feeds ok / failed</th>
              <th>New articles</th>
              <th>Duplicates</th>
              <th>Outcome</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => (
              <tr key={run.id}>
                <td>{new Date(run.started_at).toLocaleString("en")}</td>
                <td>{run.trigger}</td>
                <td>
                  {run.feeds_ok} / {run.feeds_failed}
                </td>
                <td>{run.articles_new}</td>
                <td>{run.articles_duplicate}</td>
                <td>
                  {run.error ? (
                    <span className="pill pill--warn" title={run.error}>
                      error
                    </span>
                  ) : run.deadline_reached ? (
                    <span className="pill pill--warn">deadline</span>
                  ) : run.finished_at ? (
                    <span className="pill pill--ok">ok</span>
                  ) : (
                    <span className="pill pill--warn">killed</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {runs.length === 0 && <p className="empty">No ingestion runs yet.</p>}
    </>
  );
}
