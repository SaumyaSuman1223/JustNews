/**
 * Publisher images at the size a card shows them, from the publisher's own
 * image service.
 *
 * Every picture is hot-linked from its publisher, and a feed hands over one
 * rendition: the BBC's is 240px wide and a Guardian one 140px, stretched
 * soft across a 680px hero, while others are 1200px for a 250px card. Most
 * of those services size an image by a part of its URL, so this asks each
 * for the width the layout needs - no image proxy, no third party, nothing
 * cached here. A host this does not know is returned as it is.
 *
 * Next calls this for each width in an image's `srcset` (next.config.ts,
 * `images.loaderFile`); each rule snaps to a width the service is known to
 * serve.
 */
type Loader = { src: string; width: number; quality?: number };

function snap(width: number, sizes: readonly number[]): number {
  return sizes.find((size) => size >= width) ?? sizes[sizes.length - 1]!;
}

const BBC = [240, 320, 480, 640, 800, 976] as const;
const FRANCE24 = [320, 480, 640, 800, 1024, 1280] as const;
const THE_HINDU = [480, 615, 1200] as const;
const GUARDIAN = [140, 500, 1000, 2000] as const;

export default function publisherImageLoader({ src, width }: Loader): string {
  let url: URL;
  try {
    url = new URL(src);
  } catch {
    return src;
  }

  switch (url.hostname) {
    case "ichef.bbci.co.uk": {
      // /ace/standard/240/... and /images/ic/240x135/...
      const size = snap(width, BBC);
      url.pathname = url.pathname
        .replace(/\/ace\/standard\/\d+\//, `/ace/standard/${size}/`)
        .replace(/\/images\/ic\/\d+x\d+\//, `/images/ic/${size}x${Math.round((size * 9) / 16)}/`);
      return url.toString();
    }
    case "s.france24.com":
      url.pathname = url.pathname.replace(/\/w:\d+\//, `/w:${snap(width, FRANCE24)}/`);
      return url.toString();
    case "th-i.thgim.com":
      url.pathname = url.pathname.replace(
        /\/alternates\/LANDSCAPE_\d+\//,
        `/alternates/LANDSCAPE_${snap(width, THE_HINDU)}/`,
      );
      return url.toString();
    case "i.guim.co.uk": {
      // The query is signed, so its width cannot change; the same crop is
      // served unsigned at fixed widths from media.guim.co.uk.
      const match = url.pathname.match(/^\/img\/media\/([0-9a-f]+)\/(\d+)_(\d+)_(\d+)_(\d+)\//);
      if (!match) return src;
      const [, hash, x, y, cropWidth, cropHeight] = match;
      const available = GUARDIAN.filter((size) => size <= Number(cropWidth));
      if (available.length === 0) return src;
      return `https://media.guim.co.uk/${hash}/${x}_${y}_${cropWidth}_${cropHeight}/${snap(width, available)}.jpg`;
    }
    case "platform.theverge.com":
      url.searchParams.set("w", String(Math.min(width, 1600)));
      return url.toString();
    case "live-production.wcms.abc-cdn.net.au":
      if (url.searchParams.has("width")) url.searchParams.set("width", String(width));
      return url.toString();
    default:
      return src;
  }
}
