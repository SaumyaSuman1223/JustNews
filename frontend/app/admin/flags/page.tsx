import { getFeatureFlags } from "@/lib/api";
import { requireAdmin } from "@/lib/adminGuard";
import { createFeatureFlagAction, setFeatureFlagAction } from "@/lib/adminActions";

export const metadata = { title: "Flags · Admin" };

export default async function AdminFlagsPage() {
  const access = await requireAdmin();
  if (!access.ok) return access.element;

  const flags = await getFeatureFlags(access.auth);

  return (
    <>
      <h1 style={{ fontFamily: "var(--font-display)", fontSize: "1.4rem" }}>Feature flags</h1>
      <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
        A toggle that takes effect without a deploy. A flag with no row anywhere reads as
        enabled, so creating one here never turns something off by omission - it only ever
        adds a switch.
      </p>

      <div className="admin-table-wrap">
        <table className="admin-table">
          <thead>
            <tr>
              <th>Key</th>
              <th>Description</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {flags.map((flag) => (
              <tr key={flag.key}>
                <td>
                  <code>{flag.key}</code>
                </td>
                <td style={{ whiteSpace: "normal", maxWidth: "28rem" }}>{flag.description}</td>
                <td>
                  <span className={`pill ${flag.enabled ? "pill--ok" : "pill--warn"}`}>
                    {flag.enabled ? "on" : "off"}
                  </span>
                </td>
                <td>
                  <form action={setFeatureFlagAction.bind(null, flag.key, !flag.enabled)}>
                    <button type="submit" className="card__action">
                      {flag.enabled ? "Turn off" : "Turn on"}
                    </button>
                  </form>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {flags.length === 0 && <p className="empty">No flags yet.</p>}

      <h2 style={{ fontFamily: "var(--font-display)", fontSize: "1.1rem" }}>New flag</h2>
      <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
        Created off by default - turn it on from the table above once the code that checks it
        is deployed.
      </p>
      <form action={createFeatureFlagAction} className="inline-form">
        <input type="text" name="key" placeholder="lowercase_key" required pattern="[a-z][a-z0-9_]{2,59}" />
        <input
          type="text"
          name="description"
          placeholder="What this gates"
          required
          style={{ minWidth: "16rem" }}
        />
        <button type="submit" className="button button--secondary">
          Create
        </button>
      </form>
    </>
  );
}
