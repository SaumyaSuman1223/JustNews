import { ChevronDownIcon } from "@/components/icons";
import { viewHref, type DiscoverView } from "@/lib/discoverView";
import { t, type LocaleCode } from "@/lib/i18n";

/**
 * Discover's loading forms (ADR 0014, "Rendering"). The page sends its shell
 * at once and streams the feed, then the rail, as each one's data arrives;
 * these hold their places until then.
 *
 * No hooks and no state, so the same markup serves the server's Suspense
 * fallbacks and the client's own view switches (Discover.tsx).
 */

/** The lead and its row of three - the first screen of any Discover view. */
export function FeedSkeleton() {
  return (
    <div className="discover__skeleton" aria-hidden="true">
      <div className="skel skel--lead">
        <div className="skel__text">
          <span className="skel__line skel__line--xl" />
          <span className="skel__line skel__line--xl" />
          <span className="skel__line" />
          <span className="skel__line" />
        </div>
        <span className="skel__media" />
      </div>
      <div className="skel__row">
        {[0, 1, 2].map((index) => (
          <div className="skel skel--card" key={index}>
            <span className="skel__media" />
            <span className="skel__line" />
            <span className="skel__line skel__line--short" />
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * The rail's place, held. It carries the rail's own class because the page's
 * two-column layout exists only while a `.discover-rail` does: without it
 * the feed would render full width and jump narrower when the rail arrived.
 */
export function RailSkeleton() {
  return (
    <div className="discover-rail discover-rail--loading" aria-hidden="true">
      <div className="discover-rail__widgets">
        {[0, 1, 2].map((index) => (
          <div className="rail-widget rail-widget--loading" key={index}>
            <span className="skel__line skel__line--short" />
            <span className="skel__line" />
            <span className="skel__line" />
            <span className="skel__line skel__line--short" />
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * The whole view while its first page is on the way: the real title and
 * tabs - plain links, so a view can be chosen before the feed lands - over
 * the feed's and the rail's skeletons. Its bar is the same markup
 * `DiscoverTabs` renders, so nothing moves when the live one replaces it.
 */
export function DiscoverSkeleton({ locale, view }: { locale: LocaleCode; view: DiscoverView }) {
  return (
    <div className="discover" aria-busy="true">
      <div className="discover__bar">
        <h1 className="discover__title">{t(locale, "discover.title")}</h1>
        <nav className="discover__tabs" aria-label={t(locale, "discover.tabs")}>
          <a
            className="discover__tab"
            aria-current={view.kind === "for-you" ? "page" : undefined}
            href={viewHref(locale, { kind: "for-you" })}
          >
            {t(locale, "discover.tab.forYou")}
          </a>
          <a
            className="discover__tab"
            aria-current={view.kind === "top" ? "page" : undefined}
            href={viewHref(locale, { kind: "top" })}
          >
            {t(locale, "discover.tab.top")}
          </a>
          {/* The topic menu needs the topic list, which is part of what is
              loading: its label holds the place, inert. */}
          <span
            className="discover__tab"
            aria-current={view.kind === "topic" ? "page" : undefined}
            aria-hidden="true"
          >
            {t(locale, "discover.tab.topics")}
            <ChevronDownIcon className="discover__chevron" />
          </span>
        </nav>
        <div className="discover__tools" />
      </div>
      <div className="discover__feed">
        <FeedSkeleton />
      </div>
      <div className="discover__rail-slot">
        <RailSkeleton />
      </div>
    </div>
  );
}
