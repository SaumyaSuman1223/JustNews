import type { Viewport } from "next";
import type { ReactNode } from "react";
import "./globals.css";

import { ServiceWorkerRegistration } from "@/components/ServiceWorkerRegistration";

export const viewport: Viewport = {
  themeColor: "#0f6b53",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <ServiceWorkerRegistration />
      {children}
    </>
  );
}
