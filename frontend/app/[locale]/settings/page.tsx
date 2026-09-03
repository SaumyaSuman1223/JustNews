import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { DeleteAccountButton } from "@/components/DeleteAccountButton";
import { SignInRequired } from "@/components/SignInRequired";
import { getMe } from "@/lib/api";
import { getBrowsingSessionId } from "@/lib/browsingSession";
import { updateLanguagesFormAction } from "@/lib/actions";
import { getLocale, isLocaleCode, locales, t } from "@/lib/i18n";
import { getSession } from "@/lib/session";

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

  const profile = await getMe({
    accessToken: session.accessToken,
    sessionId: await getBrowsingSessionId(),
  });
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
