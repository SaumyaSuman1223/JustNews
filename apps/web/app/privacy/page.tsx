import Link from "next/link";

export default function PrivacyPage() {
  return (
    <article style={{ lineHeight: 1.7 }}>
      <p className="notice" role="note">
        <strong>Draft, not legal advice.</strong> This describes what the system actually does
        today, written by the people who built it - it has not been reviewed by counsel and must
        be before this site is used by anyone outside a private beta.
      </p>

      <h1 style={{ fontFamily: "var(--font-display)" }}>Privacy Policy</h1>
      <p style={{ color: "var(--text-muted)" }}>Last updated: this is a working draft.</p>

      <h2>What we store about an article</h2>
      <p>
        Title, a summary of up to 300 characters, an image URL, the source name, the author if the
        publisher provides one, and a canonical link back to the original. Never the full article
        text - we always send you to the publisher to read it.
      </p>

      <h2>What we store about you</h2>
      <p>
        An account is identified by an id issued by our authentication provider (Supabase). We
        additionally store: the languages you choose for your feed, your role, whether and when
        you redeemed a beta invite, articles you save, topics you follow, and a log of articles
        you open and headlines shown to you (which article, where on the page, when, and in which
        surface - feed, search, a topic page). That last log is what lets us measure whether the
        product actually works, and eventually rank a feed instead of just listing one.
      </p>
      <p>
        We do not store your email address outside our authentication provider, and we never put
        it in application logs - only an internal id.
      </p>

      <h2>Cookies and similar technology</h2>
      <p>
        A session cookie from our authentication provider keeps you signed in. A second cookie
        groups activity from one visit together, signed in or not, so we can tell a returning
        visitor from a brand new one without knowing who they are. Neither is used for advertising
        or shared with a third party for that purpose - we do not run advertising on this site.
      </p>

      <h2>How long we keep it</h2>
      <p>
        Article metadata is kept for 90 days from ingestion, then removed. Your saves and follows
        persist until you remove them or delete your account. Interaction logs (impressions,
        clicks) persist for measurement and, in later stages, for improving what the feed shows
        you - deleting your account anonymises these rather than deleting them outright, described
        below.
      </p>

      <h2>Who can see it</h2>
      <p>
        Postgres row-level security restricts your saves, follows and history to your own account
        at the database layer, not only in application code. A small number of administrators can
        see aggregate, cross-account statistics (how many people read a story, click-through rates
        by surface) and can moderate individual articles; every administrative action is logged
        with who did it and when.
      </p>

      <h2>Your rights</h2>
      <p>
        Wherever you are, we treat the strictest applicable rule as the target - GDPR, UK GDPR,
        CCPA and India&rsquo;s DPDP all inform this. Concretely, from{" "}
        <Link href="/en/settings">Settings</Link>, signed in, you can:
      </p>
      <ul>
        <li>
          <strong>Export</strong> everything described above, as a single file.
        </li>
        <li>
          <strong>Delete your account</strong>, which removes your saves, follows and profile
          permanently, and anonymises your interaction history - it stops being linked to you, but
          is not deleted outright, since it also represents aggregate product measurement that
          does not belong to any one person once identity is removed.
        </li>
      </ul>
      <p>
        Deleting your account here does not delete your underlying sign-in account with our
        authentication provider - that is a separate step, currently manual, until this system
        integrates account deletion end to end.
      </p>

      <h2>Contact</h2>
      <p>
        This is a private beta with no public support address yet. If you are a beta participant,
        use the channel you were invited through.
      </p>
    </article>
  );
}
