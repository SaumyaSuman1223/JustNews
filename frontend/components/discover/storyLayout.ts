import type { StoryVariant } from "@/components/discover/StoryCard";
import type { DiscoverItem } from "@/lib/discoverView";
import { spreadRuns } from "@/lib/spreadRuns";

/** `position` is the card's place in the order it is drawn - which the
 * layout below may move a few slots from the order served (`item.position`,
 * what a click reports) - and is what a view report calls its rendered
 * position. */
export type Block = { variant: StoryVariant; items: { item: DiscoverItem; position: number }[] };

/**
 * The feed's rhythm: one lead, then a row of three cards and a wide feature,
 * repeating. A picture-less story never takes the lead or the feature slot
 * when one with a picture is near - those shapes are built around the photo.
 *
 * Without a lead or features it is rows of three only: a page's secondary
 * list ("More from BBC News") under a story that already leads the page.
 */
export function arrange(
  items: DiscoverItem[],
  { lead = true, features = true }: { lead?: boolean; features?: boolean } = {},
): Block[] {
  // The layout breaks up any run of one source that pages meeting created;
  // positions are assigned in drawn order once the blocks are built.
  const queue = spreadRuns(
    items.map((item) => ({ item, position: 0 })),
    (entry) => entry.item.article.source_slug,
  );
  const blocks: Block[] = [];
  // The source of the story placed last, so a picture slot does not pull a
  // third card from the same publisher next to two already there.
  const lastSource = () => {
    const block = blocks[blocks.length - 1];
    return block?.items[block.items.length - 1]?.item.article.source_slug;
  };
  // Only called while the queue is non-empty, so `splice` always yields one.
  const takeWithImage = () => {
    const avoid = lastSource();
    const near = (entry: (typeof queue)[number], i: number) =>
      i < 4 && entry.item.article.image_url;
    let index = queue.findIndex(
      (entry, i) => near(entry, i) && entry.item.article.source_slug !== avoid,
    );
    if (index < 0) index = queue.findIndex(near);
    return queue.splice(index >= 0 ? index : 0, 1);
  };
  if (lead && queue.length > 0) blocks.push({ variant: "lead", items: takeWithImage() });
  while (queue.length > 0) {
    blocks.push({ variant: "card", items: queue.splice(0, 3) });
    if (features && queue.length > 0) blocks.push({ variant: "wide", items: takeWithImage() });
  }
  let drawn = 0;
  return blocks.map((block) => ({
    ...block,
    items: block.items.map(({ item }) => ({ item, position: drawn++ })),
  }));
}
