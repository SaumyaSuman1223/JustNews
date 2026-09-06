import type { Metadata } from "next";
import { Suspense } from "react";

import { LoginForm } from "@/components/LoginForm";
import { isLocaleCode, t } from "@/lib/i18n";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return { title: t(isLocaleCode(locale) ? locale : "en", "login.title") };
}

export default function LoginPage() {
  // useSearchParams() inside LoginForm opts this subtree out of static
  // rendering unless it is wrapped here - Next's own required pattern.
  return (
    <Suspense fallback={null}>
      <LoginForm />
    </Suspense>
  );
}
