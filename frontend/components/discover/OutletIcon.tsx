"use client";

import Image from "next/image";
import { useState } from "react";

/** The origin of a URL, or "" when it is not one. */
export function originOf(url: string): string {
  try {
    return new URL(url).origin;
  } catch {
    return "";
  }
}

/** The outlet's own favicon, from its own site - the same hotlinking the
 * product already does for article images. Its initial when there is no
 * homepage to ask, or the icon does not load. */
export function OutletIcon({ name, homepage }: { name: string; homepage: string }) {
  const [failed, setFailed] = useState(false);
  let src: string | null = null;
  if (homepage) {
    try {
      src = new URL("/favicon.ico", homepage).toString();
    } catch {
      src = null;
    }
  }
  if (!src || failed) {
    return <span className="sources__icon sources__icon--letter">{name.slice(0, 1)}</span>;
  }
  return (
    <Image
      className="sources__icon"
      src={src}
      alt=""
      width={18}
      height={18}
      unoptimized
      onError={() => setFailed(true)}
    />
  );
}
