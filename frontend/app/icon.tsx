import { monogramIcon } from "@/lib/icon";

// The browser tab's icon. Next links it from every page's <head>; there was
// none, and tabs showed the browser's blank page.
export const size = { width: 64, height: 64 };
export const contentType = "image/png";

export default function Icon() {
  return monogramIcon(64);
}
