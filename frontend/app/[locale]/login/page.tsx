import type { Metadata } from "next";
import { Suspense } from "react";

import { LoginForm } from "@/components/LoginForm";

export const metadata: Metadata = { title: "Sign in" };

export default function LoginPage() {
  // useSearchParams() inside LoginForm opts this subtree out of static
  // rendering unless it is wrapped here - Next's own required pattern.
  return (
    <Suspense fallback={null}>
      <LoginForm />
    </Suspense>
  );
}
