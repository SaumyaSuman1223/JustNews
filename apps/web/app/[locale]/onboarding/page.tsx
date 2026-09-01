import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { completeOnboardingAction } from "@/lib/actions";
import { getFollows, getMe, getTopics } from "@/lib/api";
import { getLocale, isLocaleCode, locales } from "@/lib/i18n";
import { requireBetaAccess } from "@/lib/guards";

export const metadata: Metadata = { title: "Get set up" };

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
        <h1>Get set up</h1>
        <p>Two quick choices - both changeable later from Settings.</p>
      </div>

      <form action={action}>
        <div className="field">
          <label>Languages for your feed</label>
          <p className="form-note" style={{ marginBlockStart: 0 }}>
            Choose at least one.
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
          <label>What are you interested in?</label>
          <p className="form-note" style={{ marginBlockStart: 0 }}>
            Optional - pick as many as you like.
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

        <button type="submit" className="button button--primary">
          Continue
        </button>
      </form>

      <p className="form-note">
        <Link href={`/${active.code}`}>Skip for now</Link>
      </p>
    </div>
  );
}
