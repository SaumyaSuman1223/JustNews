import { getAdminTopics } from "@/lib/api";
import { requireAdmin } from "@/lib/adminGuard";

export const metadata = { title: "Taxonomy · Admin" };

export default async function AdminTaxonomyPage() {
  const access = await requireAdmin();
  if (!access.ok) return access.element;

  const topics = await getAdminTopics(access.auth, { language: "en" });

  return (
    <>
      <h1 style={{ fontFamily: "var(--font-display)", fontSize: "1.4rem" }}>Taxonomy</h1>

      <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
        The 17 top-level IPTC Media Topics concepts currently loaded. There is no deeper tree yet
        - every article is classified into one of these, never a subtopic.
      </p>

      <div className="admin-table-wrap">
        <table className="admin-table">
          <thead>
            <tr>
              <th>Id</th>
              <th>Label</th>
              <th>Articles</th>
            </tr>
          </thead>
          <tbody>
            {topics.map((topic) => (
              <tr key={topic.id}>
                <td>
                  <code>{topic.id}</code>
                </td>
                <td>{topic.label}</td>
                <td>{topic.article_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {topics.length === 0 && <p className="empty">No topics loaded.</p>}
    </>
  );
}
