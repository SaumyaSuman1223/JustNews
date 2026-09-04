import { notFound } from "next/navigation";

import { getAdminTopics, getArticleTopics } from "@/lib/api";
import { requireAdmin } from "@/lib/adminGuard";
import { setArticleTopicsAction } from "@/lib/adminActions";

export const metadata = { title: "Article topics · Admin" };

interface RouteParams {
  id: string;
}

export default async function AdminArticleTopicsPage({
  params,
}: {
  params: Promise<RouteParams>;
}) {
  const access = await requireAdmin();
  if (!access.ok) return access.element;

  const { id } = await params;
  const articleId = Number(id);
  if (!Number.isInteger(articleId)) notFound();

  const [allTopics, current] = await Promise.all([
    getAdminTopics(access.auth, { language: "en" }),
    getArticleTopics(access.auth, articleId, "en"),
  ]);
  const assigned = new Set(current.map((topic) => topic.id));
  const primary = current.find((topic) => topic.is_primary)?.id ?? current[0]?.id;

  return (
    <>
      <h1 style={{ fontFamily: "var(--font-display)", fontSize: "1.4rem" }}>
        Article {articleId} — topics
      </h1>
      <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
        An article must carry at least one topic, and exactly one of them is primary. Saving
        replaces the full set - it does not merge with what ingestion assigned.
      </p>

      <form action={setArticleTopicsAction.bind(null, articleId)}>
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Assigned</th>
                <th>Primary</th>
                <th>Id</th>
                <th>Label</th>
              </tr>
            </thead>
            <tbody>
              {allTopics.map((topic) => (
                <tr key={topic.id}>
                  <td>
                    <input
                      type="checkbox"
                      name="topicIds"
                      value={topic.id}
                      defaultChecked={assigned.has(topic.id)}
                    />
                  </td>
                  <td>
                    <input
                      type="radio"
                      name="primaryTopicId"
                      value={topic.id}
                      defaultChecked={topic.id === primary}
                    />
                  </td>
                  <td>
                    <code>{topic.id}</code>
                  </td>
                  <td>{topic.label}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <button type="submit" className="button button--secondary" style={{ marginTop: "1rem" }}>
          Save
        </button>
      </form>
    </>
  );
}
