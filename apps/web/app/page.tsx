import { redirect } from "next/navigation";
import { defaultLocale } from "@/lib/i18n";

// Stage 3 replaces this with negotiation on Accept-Language and a stored
// preference. Until then the root simply lands on the default locale.
export default function RootPage() {
  redirect(`/${defaultLocale}`);
}
