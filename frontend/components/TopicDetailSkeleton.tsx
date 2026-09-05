import { FeedSkeleton } from "@/components/FeedSkeleton";

/**
 * A My Desk topic page's loading form: title, tabs, and the same
 * `.desk-layout` split (main column + overview/related rail) the real page
 * renders into - see HomeSkeleton's own note on why a flat feed placeholder
 * would collapse that rail and then snap it wide once data lands.
 */
export function TopicDetailSkeleton() {
  return (
    <>
      <div className="page-header" aria-hidden="true">
        <div className="skeleton skeleton--lead-title" />
      </div>

      <nav className="home-tabs" aria-hidden="true">
        <ul>
          {Array.from({ length: 5 }, (_, index) => (
            <li key={index} style={{ display: "flex", alignItems: "center", blockSize: "3rem" }}>
              <div className="skeleton skeleton--tab" />
            </li>
          ))}
        </ul>
      </nav>

      <div className="desk-layout">
        <div className="desk-layout__main">
          <FeedSkeleton layout="list" secondaries={0} rows={6} />
        </div>
        <div className="desk-layout__rail">
          <div className="skeleton skeleton--panel" aria-hidden="true" />
          <div className="skeleton skeleton--panel" aria-hidden="true" />
        </div>
      </div>
    </>
  );
}
