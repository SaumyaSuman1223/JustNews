/**
 * The same items with no key running more than twice in a row: when two in
 * a row share one, the next item with a different key is brought forward.
 * Order is otherwise kept - this breaks up a run, it does not re-rank. When
 * only one key is left, the run is unavoidable and kept.
 *
 * Used on a Discover page as the server builds it, and again on the whole
 * list the reader has scrolled, since two pages that are each spread can
 * still meet in a run.
 */
export function spreadRuns<T>(items: T[], keyOf: (item: T) => string): T[] {
  const queue = [...items];
  const out: T[] = [];
  while (queue.length > 0) {
    const last = out.length > 0 ? keyOf(out[out.length - 1]!) : undefined;
    const beforeLast = out.length > 1 ? keyOf(out[out.length - 2]!) : undefined;
    const run = last !== undefined && last === beforeLast;
    const index = run ? queue.findIndex((item) => keyOf(item) !== last) : 0;
    out.push(...queue.splice(index >= 0 ? index : 0, 1));
  }
  return out;
}
