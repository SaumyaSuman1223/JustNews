import { getRemovedArticles } from "@/lib/api";
import { requireAdmin } from "@/lib/adminGuard";
import { restoreArticleAction, takedownArticleAction } from "@/lib/adminActions";

export const metadata = { title: "Moderation · Admin" };

export default async function AdminArticlesPage() {
  const access = await requireAdmin();
  if (!access.ok) return access.element;

  const removed = await getRemovedArticles(access.auth);

  return (
    <>
      <h1 style={{ fontFamily: "var(--font-display)", fontSize: "1.4rem" }}>Moderation</h1>

      <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
        Take an article down by id. There is no title search here yet - the article id shows in
        its URL (<code>/a/&#123;id&#125;</code>) on the public site.
      </p>
      <form action={takedownArticleAction} className="inline-form">
        <input type="number" name="articleId" placeholder="Article id" required />
        <input type="text" name="reason" placeholder="Reason" required style={{ minWidth: "16rem" }} />
        <button type="submit" className="button button--secondary">
          Take down
        </button>
      </form>

      <h2 style={{ fontFamily: "var(--font-display)", fontSize: "1.1rem" }}>Removed articles</h2>
      <div className="admin-table-wrap">
        <table className="admin-table">
          <thead>
            <tr>
              <th>Id</th>
              <th>Title</th>
              <th>Source</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {removed.map((article) => (
              <tr key={article.id}>
                <td>{article.id}</td>
                <td style={{ whiteSpace: "normal", maxWidth: "28rem" }}>{article.title}</td>
                <td>{article.source_name}</td>
                <td>
                  <form action={restoreArticleAction.bind(null, article.id)}>
                    <button type="submit" className="card__action">
                      Restore
                    </button>
                  </form>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {removed.length === 0 && <p className="empty">Nothing taken down.</p>}
    </>
  );
}
