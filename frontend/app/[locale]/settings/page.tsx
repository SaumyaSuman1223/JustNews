import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { DeleteAccountButton } from "@/components/DeleteAccountButton";
import { SignInRequired } from "@/components/SignInRequired";
import { getMe } from "@/lib/api";
import { getBrowsingSessionId } from "@/lib/browsingSession";
import { updateLanguagesFormAction } from "@/lib/actions";
import { getLocale, isLocaleCode, locales } from "@/lib/i18n";
import { getSession } from "@/lib/session";

export const metadata: Metadata = { title: "Settings" };

export default async function SettingsPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  if (!isLocaleCode(locale)) notFound();
  const active = getLocale(locale);
  const session = await getSession();

  if (!session) return <SignInRequired locale={active.code} path={`/${active.code}/settings`} />;

  const profile = await getMe({
    accessToken: session.accessToken,
    sessionId: await getBrowsingSessionId(),
  });
  const preferred = new Set(profile?.preferred_languages ?? []);

  return (
    <div className="narrow">
      <div className="page-header">
        <h1>Settings</h1>
        <p>Signed in as {session.email}.</p>
      </div>

      <form action={updateLanguagesFormAction}>
        <div className="field">
          <label>Languages for your feed</label>
          <p className="form-note" style={{ marginBlockStart: 0 }}>
            Choose at least one. Your feed only ever shows languages you pick here.
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
          Save
        </button>
      </form>

      <div className="page-header" style={{ marginBlockStart: "var(--space-8)" }}>
        <h2 style={{ fontFamily: "var(--font-display)", fontSize: "1.2rem" }}>Your data</h2>
        <p>
          Read what this applies to in the <Link href="/privacy">privacy policy</Link>.
        </p>
      </div>
      <p>
        <a className="button button--secondary" href="/api/export" download="justnews-data.json">
          Download your data
        </a>
      </p>
      <DeleteAccountButton locale={active.code} />
    </div>
  );
}
