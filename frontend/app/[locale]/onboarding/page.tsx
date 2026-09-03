import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { completeOnboardingAction } from "@/lib/actions";
import { getFollows, getMe, getTopics } from "@/lib/api";
import { getLocale, isLocaleCode, locales, t } from "@/lib/i18n";
import { requireBetaAccess } from "@/lib/guards";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return { title: t(isLocaleCode(locale) ? locale : "en", "onboarding.heading") };
}

export default async function OnboardingPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  if (!isLocaleCode(locale)) notFound();
  const active = getLocale(locale);

  const access = await requireBetaAccess(active.code, `/${active.code}/onboarding`);
  if (!access.ok) return access.element;

  const [topics, followed, profile] = await Promise.all([
    getTopics(active.code),
    getFollows(access.auth).then((rows) => new Set(rows.map((row) => row.topic_id))),
    getMe(access.auth),
  ]);
  const preferredLanguages = new Set(
    profile?.preferred_languages.length ? profile.preferred_languages : [active.code],
  );

  const action = completeOnboardingAction.bind(null, active.code);

  return (
    <div className="narrow">
      <div className="page-header">
        <h1>{t(active.code, "onboarding.heading")}</h1>
        <p>{t(active.code, "onboarding.intro")}</p>
      </div>

      <form action={action}>
        <div className="field">
          <label>{t(active.code, "settings.languages.label")}</label>
          <p className="form-note" style={{ marginBlockStart: 0 }}>
            {t(active.code, "onboarding.languages.note")}
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
                  defaultChecked={preferredLanguages.has(option.code)}
                />
                {option.label}
              </label>
            </li>
          ))}
        </ul>

        <div className="field" style={{ marginBlockStart: "var(--space-6)" }}>
          <label>{t(active.code, "onboarding.topics.label")}</label>
          <p className="form-note" style={{ marginBlockStart: 0 }}>
            {t(active.code, "onboarding.topics.note")}
          </p>
        </div>
        <ul className="checkbox-grid">
          {topics.data.map((topic) => (
            <li key={topic.id}>
              <label>
                <input
                  type="checkbox"
                  name="topics"
                  value={topic.id}
                  defaultChecked={followed.has(topic.id)}
                />
                {topic.label}
              </label>
            </li>
          ))}
        </ul>

        {/* True today, not a promise about later: anyone who reaches this
            page already has beta access (requireBetaAccess above), so these
            picks feed the real heuristic ranker (backend/.../ranking.py)
            immediately - not a preference stored for a model that doesn't
            exist yet. */}
        <p className="form-note">{t(active.code, "onboarding.shapesFeed")}</p>

        <button type="submit" className="button button--primary">
          {t(active.code, "onboarding.continue")}
        </button>
      </form>

      <p className="form-note">
        <Link href={`/${active.code}`}>{t(active.code, "onboarding.skip")}</Link>
      </p>
    </div>
  );
}
