import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { ExplorationDeck } from "@/components/ExplorationDeck";
import { FollowTopicChip } from "@/components/FollowTopicChip";
import { completeOnboardingAction } from "@/lib/actions";
import {
  getExplorationDeck,
  getFollowedSources,
  getFollows,
  getMe,
  getSources,
  getTopics,
  type SourceOption,
} from "@/lib/api";
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

  const [deck, profile, followedSourceIds, topics, followedTopicIds] = await Promise.all([
    getExplorationDeck(access.auth, { locale: active.code }),
    getMe(access.auth),
    getFollowedSources(access.auth).then((rows) => new Set(rows.map((row) => row.source_id))),
    getTopics(active.code),
    getFollows(access.auth).then((rows) => new Set(rows.map((row) => row.topic_id))),
  ]);
  const preferredLanguages = new Set(
    profile?.preferred_languages.length ? profile.preferred_languages : [active.code],
  );

  // Seeded from the reader's languages as they stand right now, not from
  // whatever the language checkboxes below are checked to when the form is
  // submitted - this page has no client JS to react to that live, and a
  // reader picking a new language for the first time meets its sources on
  // their next visit here, not mid-scroll on this one.
  const sourcesByLanguage = await Promise.all(
    [...preferredLanguages].map((language) => getSources(language)),
  );
  const sources: SourceOption[] = sourcesByLanguage.flatMap((page) => page.data);

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

        {/* Before topics, not after: for a reader who already reads two
            named outlets daily, which source they trust is a faster,
            more legible signal than which IPTC topic covers it. */}
        {sources.length > 0 && (
          <>
            <div className="field" style={{ marginBlockStart: "var(--space-6)" }}>
              <label>{t(active.code, "onboarding.sources.label")}</label>
              <p className="form-note" style={{ marginBlockStart: 0 }}>
                {t(active.code, "onboarding.sources.note")}
              </p>
            </div>
            <ul className="checkbox-grid">
              {sources.map((source) => (
                <li key={source.id}>
                  <label>
                    <input
                      type="checkbox"
                      name="sources"
                      value={source.id}
                      defaultChecked={followedSourceIds.has(source.id)}
                    />
                    {source.name}
                  </label>
                </li>
              ))}
            </ul>
          </>
        )}

        <div className="field" style={{ marginBlockStart: "var(--space-6)" }}>
          <label>{t(active.code, "onboarding.deck.heading")}</label>
          <p className="form-note" style={{ marginBlockStart: 0 }}>
            {t(active.code, "onboarding.deck.intro")}
          </p>
        </div>
        {deck.data.length > 0 ? (
          <ExplorationDeck cards={deck.data} locale={active.code} signedIn />
        ) : (
          <p className="empty">{t(active.code, "onboarding.deck.empty")}</p>
        )}

        {/* The deck infers interest from behaviour; this is the direct
            alternative for a reader who already knows what they want and
            would rather tap a category than sample twenty cards. Both
            paths write the same UserFollow row - neither is more "real"
            than the other. */}
        {topics.data.length > 0 && (
          <>
            <div className="field" style={{ marginBlockStart: "var(--space-6)" }}>
              <label>{t(active.code, "onboarding.categories.label")}</label>
              <p className="form-note" style={{ marginBlockStart: 0 }}>
                {t(active.code, "onboarding.categories.note")}
              </p>
            </div>
            <ul className="chip-list">
              {topics.data.map((topic) => (
                <li key={topic.id}>
                  <FollowTopicChip
                    topicId={topic.id}
                    label={topic.label}
                    locale={active.code}
                    following={followedTopicIds.has(topic.id)}
                    revalidatePath={`/${active.code}/onboarding`}
                  />
                </li>
              ))}
            </ul>
          </>
        )}

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
