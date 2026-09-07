/**
 * The loading form of a composed feed.
 *
 * It reproduces the card size set rather than showing generic grey boxes,
 * because the design system's zero-CLS rule only holds if the placeholder
 * reserves the space the real card will take. A uniform skeleton under a
 * non-uniform feed guarantees a jump on hydration.
 */
export function FeedSkeleton({
  lead = true,
  secondaries = 4,
  compacts = 0,
  rows = 6,
  layout = "edited",
}: {
  /** Home's second tier leads with pictures rather than a lead card. */
  lead?: boolean;
  secondaries?: number;
  /** Text-only entries, as Home's second tier renders under its two picture
   * stories. Reserved here for the same reason as everything else in this
   * file: a placeholder that does not match the composition is a jump. */
  compacts?: number;
  rows?: number;
  /** Mirrors FeedList's own `layout` prop: `list` is what saved, history and
   * search actually render (every row the same weight, no lead/secondary
   * band), so their skeleton has to match or the real content jumps the
   * moment it replaces the placeholder. */
  layout?: "edited" | "list";
}) {
  return (
    <ul className={`feed feed--${layout}`} aria-hidden="true">
      {layout === "edited" && (
        <>
          {lead && (
            <li className="card card--lead">
              <div className="card__frame">
                <div className="skeleton skeleton--media" />
              </div>
              <div className="card__body">
                <div className="skeleton skeleton--title" />
                <div className="skeleton skeleton--title skeleton--mid" />
                <div className="skeleton skeleton--line" />
                <div className="skeleton skeleton--line skeleton--short" />
              </div>
            </li>
          )}

          {Array.from({ length: secondaries }, (_, index) => (
            <li key={`secondary-${index}`} className="card card--secondary">
              <div className="card__frame">
                <div className="skeleton skeleton--media" />
              </div>
              <div className="card__body">
                <div className="skeleton skeleton--title" />
                <div className="skeleton skeleton--line skeleton--mid" />
                <div className="skeleton skeleton--line skeleton--short" />
              </div>
            </li>
          ))}

          {Array.from({ length: compacts }, (_, index) => (
            <li key={`compact-${index}`} className="card card--compact">
              <div className="card__body">
                <div className="skeleton skeleton--title" />
                <div className="skeleton skeleton--line skeleton--short" />
              </div>
            </li>
          ))}
        </>
      )}

      {Array.from({ length: rows }, (_, index) => (
        <li key={`row-${index}`} className="card card--list">
          <div className="card__frame">
            <div className="skeleton skeleton--media" />
          </div>
          <div className="card__body">
            <div className="skeleton skeleton--title" />
            <div className="skeleton skeleton--line skeleton--short" />
          </div>
        </li>
      ))}
    </ul>
  );
}
