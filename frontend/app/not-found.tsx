import Link from "next/link";
import { defaultLocale } from "@/lib/i18n";

export default function NotFound() {
  return (
    <html lang="en">
      <body>
        <div className="shell">
          <main id="main" className="empty" style={{ marginBlockStart: "4rem" }}>
            <h1>That page does not exist</h1>
            <p>
              <Link href={`/${defaultLocale}`}>Go to the front page</Link>
            </p>
          </main>
        </div>
      </body>
    </html>
  );
}
