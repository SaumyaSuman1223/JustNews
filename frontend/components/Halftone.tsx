import Image from "next/image";

/**
 * The Aquila print treatment: photographs printed in colour, through a dot
 * screen - the way a newspaper prints a colour picture.
 *
 * Audit §19 asks every Aquila image to carry the same halftone. This does it
 * with an SVG filter and a CSS dot screen, on the publisher's own hotlinked
 * image - nothing is re-encoded and no derivative is stored. That is the
 * whole reason for the approach: processing images server-side would mean
 * re-hosting copies of other people's photographs, which costs money on a
 * free tier, carries terms-of-service exposure, and contradicts the product's
 * standing rule that it never stores content and always links out.
 *
 * The cost is fidelity. A filter cannot threshold per pixel against a screen
 * the way a real halftone does, so this is an impression of one: luminance,
 * a press curve per ink channel, under a regular dot grid. At reading distance it reads as newsprint. Under a magnifier it is
 * not a rosette, and it never will be. Colour survives, held a little below
 * the original's saturation and warmed toward the paper, because newsprint
 * ink is duller than a screen and a full-strength photograph on this sheet
 * reads as pasted on rather than printed.
 *
 * It is also one line to remove. `filter: none` on `.halftone img` and
 * deleting the `::after` returns every image to its original, which is what
 * makes this safe to try.
 */

/** The filter itself, mounted once per document by the reader layout. */
export function HalftoneDefs() {
  return (
    <svg className="halftone-defs" aria-hidden="true" focusable="false">
      <defs>
        {/* sRGB, not linearRGB: the default would do this in linear light and
            the midtones come out muddy, which is the opposite of a press. */}
        <filter id="aquila-halftone" colorInterpolationFilters="sRGB">
          {/* Newsprint colour: a little less saturated than the screen
              original. */}
          <feColorMatrix type="saturate" values="0.82" />
          {/* A press curve per channel - deeper shadows, highlights that stop
              at the paper rather than at white, and a slight warm cast (red
              lifted, blue held back) so the picture sits in the cream sheet
              instead of on top of it. */}
          <feComponentTransfer>
            <feFuncR type="table" tableValues="0.07 0.27 0.53 0.79 0.97" />
            <feFuncG type="table" tableValues="0.06 0.25 0.5 0.76 0.94" />
            <feFuncB type="table" tableValues="0.07 0.22 0.44 0.69 0.88" />
          </feComponentTransfer>
        </filter>
      </defs>
    </svg>
  );
}

/**
 * One image under the treatment.
 *
 * `scale` sets the dot pitch: §19 asks for 2-4px on large images and 1.5-3px
 * on small ones, because a dot that does not change with the picture reads as
 * a texture laid over it rather than the picture being printed.
 */
export function HalftoneImage({
  src,
  className,
  width,
  height,
  sizes,
  priority,
  scale = "lg",
}: {
  src: string;
  className: string;
  width: number;
  height: number;
  sizes: string;
  priority?: boolean;
  scale?: "lg" | "sm";
}) {
  return (
    <span className={`halftone halftone--${scale} ${className}`}>
      {/* `unoptimized`, like every other image in the product: the source is
          the publisher's own CDN and next/image would need each of those
          hosts in remotePatterns. */}
      <Image
        src={src}
        alt=""
        width={width}
        height={height}
        sizes={sizes}
        unoptimized
        priority={priority}
      />
    </span>
  );
}
