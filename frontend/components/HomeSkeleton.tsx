import { FeedSkeleton } from "@/components/FeedSkeleton";

/**
 * Home's loading form: the same `.home` grid the real page renders into -
 * three tiers, rail, tabbed feed - reserved ahead of the data. A flat feed
 * skeleton here would collapse the rail to nothing and then snap it wide
 * the moment the real content lands, which is exactly the jump the design
 * system's zero-CLS rule exists to prevent.
 *
 * The tier headings are reserved too. They are a rule and a line of type
 * above each level, so omitting them would shift all three tiers upward at
 * the moment the data arrives.
 */
export function HomeSkeleton() {
  return (
    <>
      <div className="home-greeting" aria-hidden="true">
        <div className="home-greeting__standing">
          <div className="skeleton skeleton--line skeleton--short" />
        </div>
        <div className="skeleton skeleton--line skeleton--short" />
        <div className="skeleton skeleton--lead-title" />
      </div>

      <div className="home">
        <div className="home__hero">
          <div className="home-tier" aria-hidden="true">
            <div className="skeleton skeleton--tab" />
          </div>
          <FeedSkeleton secondaries={2} rows={0} />
        </div>

        <div className="home__know">
          <div className="home-tier" aria-hidden="true">
            <div className="skeleton skeleton--tab" />
          </div>
          <FeedSkeleton lead={false} secondaries={2} compacts={4} rows={0} />
        </div>

        <div className="home__rail">
          <div className="skeleton skeleton--panel" aria-hidden="true" />
          <div className="skeleton skeleton--panel" aria-hidden="true" />
          <div className="skeleton skeleton--panel skeleton--panel--tall" aria-hidden="true" />
        </div>

        <div className="home__feed">
          <div className="home-tier" aria-hidden="true">
            <div className="skeleton skeleton--tab" />
          </div>
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
