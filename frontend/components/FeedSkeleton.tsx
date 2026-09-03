/**
 * The loading form of a composed feed.
 *
 * It reproduces the card size set rather than showing generic grey boxes,
 * because the design system's zero-CLS rule only holds if the placeholder
 * reserves the space the real card will take. A uniform skeleton under a
 * non-uniform feed guarantees a jump on hydration.
 */
export function FeedSkeleton({ secondaries = 4, rows = 6 }: { secondaries?: number; rows?: number }) {
  return (
    <ul className="feed" aria-hidden="true">
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
