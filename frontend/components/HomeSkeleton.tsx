import { FeedSkeleton } from "@/components/FeedSkeleton";

/**
 * Home's loading form: the same `.home` grid the real page renders into -
 * hero, rail, tabbed feed - reserved ahead of the data. A flat feed
 * skeleton here would collapse the rail to nothing and then snap it wide
 * the moment the real content lands, which is exactly the jump the design
 * system's zero-CLS rule exists to prevent.
 */
export function HomeSkeleton() {
  return (
    <>
      <div className="home-greeting" aria-hidden="true">
        <div className="skeleton skeleton--line skeleton--short" />
        <div className="skeleton skeleton--lead-title" />
      </div>

      <div className="home">
        <div className="home__hero">
          <FeedSkeleton secondaries={4} rows={0} />
        </div>

        <div className="home__rail">
          <div className="skeleton skeleton--panel" aria-hidden="true" />
          <div className="skeleton skeleton--panel" aria-hidden="true" />
          <div className="skeleton skeleton--panel skeleton--panel--tall" aria-hidden="true" />
        </div>

        <div className="home__feed">
          <nav className="home-tabs" aria-hidden="true">
            <ul>
              <li style={{ display: "flex", alignItems: "center", blockSize: "3rem" }}>
                <div className="skeleton skeleton--tab" />
              </li>
              <li style={{ display: "flex", alignItems: "center", blockSize: "3rem" }}>
                <div className="skeleton skeleton--tab" />
              </li>
            </ul>
          </nav>
          <FeedSkeleton layout="list" secondaries={0} rows={6} />
        </div>
      </div>
    </>
  );
}
