import type { StoryVariant } from "@/components/discover/StoryCard";
import type { DiscoverItem } from "@/lib/discoverView";

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
  const queue = items.map((item, position) => ({ item, position }));
  const blocks: Block[] = [];
  // Only called while the queue is non-empty, so `splice` always yields one.
  const takeWithImage = () => {
    const index = queue.findIndex((entry, i) => i < 4 && entry.item.article.image_url);
    return queue.splice(index >= 0 ? index : 0, 1);
  };
  if (lead && queue.length > 0) blocks.push({ variant: "lead", items: takeWithImage() });
  while (queue.length > 0) {
    blocks.push({ variant: "card", items: queue.splice(0, 3) });
    if (features && queue.length > 0) blocks.push({ variant: "wide", items: takeWithImage() });
  }
  return blocks;
}
