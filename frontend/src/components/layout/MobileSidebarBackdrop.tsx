/**
 * frontend/src/components/layout/MobileSidebarBackdrop.tsx
 * Faz 6 — Mobil sidebar açıkken arkayı karartır ve tıklanınca kapatır.
 */

"use client";

import { useAppStore } from "@/stores/appStore";

export function MobileSidebarBackdrop() {
  const sidebarMobileOpen = useAppStore((s) => s.sidebarMobileOpen);
  const closeSidebarMobile = useAppStore((s) => s.closeSidebarMobile);

  if (!sidebarMobileOpen) return null;

  return (
    <div
      className="fixed inset-0 z-30 bg-black/40 md:hidden"
      onClick={closeSidebarMobile}
      aria-hidden="true"
    />
  );
}
