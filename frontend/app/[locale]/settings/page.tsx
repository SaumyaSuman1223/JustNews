import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { DeleteAccountButton } from "@/components/DeleteAccountButton";
import { SignInRequired } from "@/components/SignInRequired";
import { getHistory, getMe } from "@/lib/api";
import { getBrowsingSessionId } from "@/lib/browsingSession";
import { updateLanguagesFormAction } from "@/lib/actions";
import type { AuthContext } from "@/lib/guards";
import { getLocale, isLocaleCode, locales, t } from "@/lib/i18n";
import { getSession } from "@/lib/session";

/**
 * The reader's own honest mirror: what they've actually been reading, by
 * language, next to what they told Settings they want. Computed from
 * history, capped rather than exhaustive - `/v1/history` tops out at 50 rows
 * a request, and a full-history read for every settings-page view would be
 * real, avoidable latency on a route that renders on every visit. Three
 * pages (150 reads, or fewer for a newer reader) is a real sample without
 * turning a settings page into a report. `null` means the call itself failed
 * (degraded, or history isn't reachable pre-beta) - a real absence,
 * rendered as nothing, not an empty chart standing in for one.
 */
async function getRecentLanguageMix(
  auth: AuthContext,
): Promise<{ rows: { language: string; count: number }[]; sampled: number } | null> {
  const PAGE_SIZE = 50;
  const MAX_PAGES = 3;
  const counts = new Map<string, number>();
  let cursor: string | undefined;
  let sampled = 0;

  for (let page = 0; page < MAX_PAGES; page++) {
    const result = await getHistory(auth, cursor, PAGE_SIZE);
    if (result.degraded) return null;
    for (const item of result.data.items) {
      counts.set(item.article.language, (counts.get(item.article.language) ?? 0) + 1);
      sampled += 1;
    }
    if (!result.data.next_cursor) break;
    cursor = result.data.next_cursor;
  }

  const rows = [...counts.entries()]
    .map(([language, count]) => ({ language, count }))
    .sort((a, b) => b.count - a.count);
  return { rows, sampled };
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return { title: t(isLocaleCode(locale) ? locale : "en", "settings.heading") };
}

export default async function SettingsPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  if (!isLocaleCode(locale)) notFound();
  const active = getLocale(locale);
  const session = await getSession();

  if (!session) return <SignInRequired locale={active.code} path={`/${active.code}/settings`} />;

  const auth = { accessToken: session.accessToken, sessionId: await getBrowsingSessionId() };
  const [profile, languageMix] = await Promise.all([getMe(auth), getRecentLanguageMix(auth)]);
  const preferred = new Set(profile?.preferred_languages ?? []);

  return (
    <div className="narrow">
      <div className="page-header">
        <h1>{t(active.code, "settings.heading")}</h1>
        {/* A session without an email is possible on paper; the old copy
            rendered "Signed in as ." when it happened. */}
        {session.email && (
          <p>{t(active.code, "settings.signedInAs", { email: session.email })}</p>
        )}
      </div>

      <form action={updateLanguagesFormAction}>
        <div className="field">
          <label>{t(active.code, "settings.languages.label")}</label>
          <p className="form-note" style={{ marginBlockStart: 0 }}>
            {t(active.code, "settings.languages.note")}
          </p>
        </div>
        <ul className="checkbox-grid">
          {locales.map((option) => (
            <li key={option.code}>
              <label>
                <input
                  type="checkbox"
                  name="languages"
                  value={option.code}
                  defaultChecked={preferred.has(option.code)}
                />
                {option.label}
              </label>
            </li>
          ))}
        </ul>
        <button type="submit" className="button button--primary">
          {t(active.code, "settings.save")}
        </button>
      </form>

      {languageMix && (
        <div className="page-header" style={{ marginBlockStart: "var(--space-8)" }}>
          <h2 style={{ fontFamily: "var(--font-display)", fontSize: "1.2rem" }}>
            {t(active.code, "profile.languageMix.heading")}
          </h2>
          {languageMix.rows.length > 0 ? (
            <>
              <p>{t(active.code, "profile.languageMix.body", { count: languageMix.sampled })}</p>
              <ul className="language-mix">
                {languageMix.rows.map((row) => {
                  const known = locales.find((option) => option.code === row.language);
                  const pct = Math.round((row.count / languageMix.sampled) * 100);
                  return (
                    <li key={row.language} className="language-mix__row">
                      <span
                        className="language-mix__label"
                        lang={known?.htmlLang ?? row.language}
                      >
                        {known?.label ?? row.language}
                      </span>
                      <span className="language-mix__track">
                        <span className="language-mix__bar" style={{ inlineSize: `${pct}%` }} />
                      </span>
                      <span className="language-mix__count">
                        {t(active.code, "profile.languageMix.count", { count: row.count })} ·{" "}
                        {pct.toLocaleString(active.code)}%
                      </span>
                    </li>
                  );
                })}
              </ul>
            </>
          ) : (
            <p>{t(active.code, "profile.languageMix.empty")}</p>
          )}
        </div>
      )}

      <div className="page-header" style={{ marginBlockStart: "var(--space-8)" }}>
        <h2 style={{ fontFamily: "var(--font-display)", fontSize: "1.2rem" }}>
          {t(active.code, "settings.yourData")}
        </h2>
        {/* The link is the whole sentence rather than two words inside one.
            A sentence split around an inline link only reassembles correctly
            in languages that put the clause in the same place. */}
        <p>
          <Link href="/privacy">{t(active.code, "settings.privacyPolicy")}</Link>
        </p>
      </div>
      <p>
        <a className="button button--secondary" href="/api/export" download="justnews-data.json">
          {t(active.code, "settings.download")}
        </a>
      </p>
      <DeleteAccountButton locale={active.code} />
    </div>
  );
}
