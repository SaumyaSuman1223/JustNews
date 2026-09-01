import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { completeOnboardingAction } from "@/lib/actions";
import { getFollows, getTopics } from "@/lib/api";
import { getBrowsingSessionId } from "@/lib/browsingSession";
import { getLocale, isLocaleCode } from "@/lib/i18n";
import { getSession } from "@/lib/session";

export const metadata: Metadata = { title: "Choose your topics" };

export default async function OnboardingPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  if (!isLocaleCode(locale)) notFound();
  const active = getLocale(locale);
  const session = await getSession();

  const [topics, followed] = await Promise.all([
    getTopics(active.code),
    session
      ? getFollows({
          accessToken: session.accessToken,
          sessionId: await getBrowsingSessionId(),
        }).then((rows) => new Set(rows.map((row) => row.topic_id)))
      : Promise.resolve(new Set<string>()),
  ]);

  const action = completeOnboardingAction.bind(null, active.code);

  return (
    <div className="narrow">
      <div className="page-header">
        <h1>What are you interested in?</h1>
        <p>Pick as many as you like. This shapes your feed - you can change it any time.</p>
      </div>

      <form action={action}>
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
