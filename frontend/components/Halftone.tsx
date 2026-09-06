import Image from "next/image";

/**
 * The Aquila print treatment: photographs reduced to a warm two-tone screen.
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
 * flattened to five tonal steps between ink and paper, under a regular dot
 * grid. At reading distance it reads as newsprint. Under a magnifier it is
 * not a rosette, and it never will be.
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
          {/* Rec. 709 luminance into all three channels - a real desaturation
              rather than an average, so a red jacket and a blue sky do not
              collapse to the same grey. */}
          <feColorMatrix
            type="matrix"
            values="0.2126 0.7152 0.0722 0 0
                    0.2126 0.7152 0.0722 0 0
                    0.2126 0.7152 0.0722 0 0
                    0 0 0 1 0"
          />
          {/* Five steps, not a curve: §19 asks for a limited tonal range, and
              a press has a limited number of tones by construction. The
              channels differ slightly so the result lands warm - ink at the
              shadow end, paper at the highlight end - rather than neutral
              grey, which would sit on this cream like a photocopy. */}
          <feComponentTransfer>
            <feFuncR type="table" tableValues="0.09 0.22 0.46 0.74 0.94" />
            <feFuncG type="table" tableValues="0.09 0.21 0.44 0.72 0.92" />
            <feFuncB type="table" tableValues="0.10 0.19 0.39 0.65 0.86" />
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
