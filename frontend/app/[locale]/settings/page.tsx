import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { DeleteAccountButton } from "@/components/DeleteAccountButton";
import { SignInRequired } from "@/components/SignInRequired";
import { getMe, getReadingProfile } from "@/lib/api";
import { getBrowsingSessionId } from "@/lib/browsingSession";
import { updateLanguagesFormAction } from "@/lib/actions";
import { getLocale, isLocaleCode, locales, t, type LocaleCode } from "@/lib/i18n";
import { getSession } from "@/lib/session";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return { title: t(isLocaleCode(locale) ? locale : "en", "settings.heading") };
}

/** A proportional bar row, shared by the language and topic breakdowns. */
function MixRow({
  label,
  lang,
  count,
  pct,
  locale,
}: {
  label: string;
  lang?: string;
  count: number;
  pct: number;
  locale: LocaleCode;
}) {
  return (
    <li className="reading-mix__row">
      <span className="reading-mix__label" lang={lang}>
        {label}
      </span>
      <span className="reading-mix__track">
        <span className="reading-mix__bar" style={{ inlineSize: `${pct}%` }} />
      </span>
      <span className="reading-mix__count">
        {t(locale, "profile.languageMix.count", { count })} · {pct.toLocaleString(locale)}%
      </span>
    </li>
  );
}

export default async function SettingsPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  if (!isLocaleCode(locale)) notFound();
  const active = getLocale(locale);
  const session = await getSession();

  if (!session) return <SignInRequired locale={active.code} path={`/${active.code}/settings`} />;

  const auth = { accessToken: session.accessToken, sessionId: await getBrowsingSessionId() };
  const [profile, readingProfile] = await Promise.all([
    getMe(auth),
    getReadingProfile(auth, active.code),
  ]);
  const preferred = new Set(profile?.preferred_languages ?? []);
  // The topic axis's own total, not readingProfile.sampled (the language
  // axis's count): not every read article carries an assigned primary
  // topic, so the two axes can sum to different totals, and each needs its
  // own denominator.
  const topicTotal =
    readingProfile?.topics.reduce((sum, entry) => sum + entry.count, 0) ?? 0;

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

      {readingProfile && (
        <div className="page-header" style={{ marginBlockStart: "var(--space-8)" }}>
          <h2 style={{ fontFamily: "var(--font-display)", fontSize: "1.2rem" }}>
            {t(active.code, "profile.languageMix.heading")}
          </h2>
          {readingProfile.sampled > 0 ? (
            <>
              <p>
                {t(active.code, "profile.languageMix.body", { count: readingProfile.sampled })}
              </p>

              <h3 className="reading-mix__subheading">{t(active.code, "profile.byLanguage")}</h3>
              <ul className="reading-mix">
                {readingProfile.languages.map((row) => {
                  const known = locales.find((option) => option.code === row.language);
                  const pct = Math.round((row.count / readingProfile.sampled) * 100);
                  return (
                    <MixRow
                      key={row.language}
                      label={known?.label ?? row.language}
                      lang={known?.htmlLang ?? row.language}
                      count={row.count}
                      pct={pct}
                      locale={active.code}
                    />
                  );
                })}
              </ul>

              {readingProfile.topics.length > 0 && (
                <>
                  <h3 className="reading-mix__subheading">{t(active.code, "profile.byTopic")}</h3>
                  <ul className="reading-mix">
                    {readingProfile.topics.map((row) => (
                      <MixRow
                        key={row.topic_id}
                        label={row.label}
                        count={row.count}
                        pct={Math.round((row.count / topicTotal) * 100)}
                        locale={active.code}
                      />
                    ))}
                  </ul>
                </>
              )}
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
          <Link href={`/${active.code}/privacy`}>{t(active.code, "settings.privacyPolicy")}</Link>
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
