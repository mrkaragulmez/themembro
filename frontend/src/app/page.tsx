/**
 * frontend/src/app/page.tsx
 * Faz 6 — Root: /dashboard'a yönlendir
 */

import { redirect } from "next/navigation";

export default function RootPage() {
  redirect("/dashboard");
}
