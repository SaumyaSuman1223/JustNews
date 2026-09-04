import { FeedSkeleton } from "@/components/FeedSkeleton";

/**
 * For a route whose `<h1>` is itself data (a topic's or edition's name), not
 * static copy - the feed/explore pattern of keeping the header outside
 * Suspense only works when the header has nothing to wait on. Here it does,
 * so the whole thing suspends together.
 */
export function PageHeaderSkeleton() {
  return (
    <>
      <div className="page-header" aria-hidden="true">
        <div className="skeleton skeleton--lead-title" />
        <div className="skeleton skeleton--line skeleton--mid" />
      </div>
      <FeedSkeleton />
    </>
  );
}
