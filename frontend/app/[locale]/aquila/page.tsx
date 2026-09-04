import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { EmptyState } from "@/components/EmptyState";
import { IssueReader } from "@/components/IssueReader";
import { getIssue, getIssueEditions, getIssuePage, getLatestIssue } from "@/lib/api";
import { getBrowsingSessionId } from "@/lib/browsingSession";
import { getLocale, isLocaleCode, t } from "@/lib/i18n";
import { getSession } from "@/lib/session";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return {
    title: t(isLocaleCode(locale) ? locale : "en", "aquila.title"),
    description: null,
  };
}

// A page logs the impressions it served, so this cannot be statically
// rendered or shared from a cache - two readers must not be attributed the
// same impression rows.
export const dynamic = "force-dynamic";

export default async function AquilaPage({
  params,
  searchParams,
}: {
  params: Promise<{ locale: string }>;
  searchParams: Promise<{ issue?: string }>;
}) {
  const { locale } = await params;
  if (!isLocaleCode(locale)) notFound();
  const active = getLocale(locale);
  const { issue: issueParam } = await searchParams;

  // Aquila has no beta gate and no sign-in requirement: it is the same paper
  // for every reader in a locale, and a signed-out visitor is exactly who a
  // publication is for.
  const session = await getSession();
  const auth = session
    ? { accessToken: session.accessToken, sessionId: await getBrowsingSessionId() }
    : null;

  // `?issue=` reaches a specific edition - the archive that freezing
  // composition buys (ADR 0012), and what the edition selector links to.
  const requested = Number(issueParam);
  const issue =
    Number.isInteger(requested) && requested > 0
      ? await getIssue(auth, { issueId: requested, locale: active.code })
      : await getLatestIssue(auth, { locale: active.code });

  return (
    <>
      <meta name="description" content={t(active.code, "site.description")} />
      {issue === null ? (
        // Not an error state. A publication that has not published yet is a
        // real thing, and this is what it looks like.
        <div className="narrow">
          <div className="page-header">
            <p className="eyebrow">{t(active.code, "aquila.standfirst")}</p>
            <h1>{t(active.code, "aquila.title")}</h1>
          </div>
          <EmptyState
            title={t(active.code, "aquila.none.title")}
            body={t(active.code, "aquila.none.body")}
            action={{ href: `/${active.code}`, label: t(active.code, "aquila.none.action") }}
          />
        </div>
      ) : (
        <AquilaIssue issue={issue} locale={active.code} dir={active.dir} auth={auth} />
      )}
    </>
  );
}

async function AquilaIssue({
  issue,
  locale,
  dir,
  auth,
}: {
  issue: NonNullable<Awaited<ReturnType<typeof getLatestIssue>>>;
  locale: ReturnType<typeof getLocale>["code"];
  dir: ReturnType<typeof getLocale>["dir"];
  auth: { accessToken: string; sessionId: string | null } | null;
}) {
  const [firstPage, editions] = await Promise.all([
    getIssuePage(auth, { issueId: issue.id, pageNo: 1, locale }),
    getIssueEditions(auth, { locale }),
  ]);

  if (firstPage === null) {
    return (
      <div className="narrow">
        <EmptyState
          title={t(locale, "aquila.none.title")}
          body={t(locale, "aquila.none.body")}
          action={{ href: `/${locale}`, label: t(locale, "aquila.none.action") }}
        />
      </div>
    );
  }

  return (
    <>
      <IssueReader
        issue={issue}
        firstPage={firstPage}
        editions={editions}
        locale={locale}
        dir={dir}
      />
      {/* The archive is not a browsable surface yet; this is the honest
          version of "there is more than today's paper" - a link back to the
          front page rather than a promise of an index that does not exist. */}
      <p className="form-note aquila__note">
        <Link href={`/${locale}`}>{t(locale, "aquila.backHome")}</Link>
      </p>
    </>
  );
}
