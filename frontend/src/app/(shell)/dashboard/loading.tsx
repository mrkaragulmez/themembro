/**
 * frontend/src/app/(shell)/dashboard/loading.tsx
 * Faz 6.4 — Dashboard yüklenme ekranı (Next.js suspense skeleton)
 */

import { Skeleton } from "@/components/ui/skeleton";

export default function DashboardLoading() {
  return (
    <div className="max-w-4xl mx-auto px-6 py-8 space-y-8">
      {/* Selamlama */}
      <Skeleton className="h-8 w-64" />

      {/* Hızlı Aksiyonlar */}
      <div className="grid grid-cols-3 gap-4">
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-24 rounded-2xl" />
        ))}
      </div>

      {/* İçerik grid */}
      <div className="grid grid-cols-2 gap-6">
        <Skeleton className="h-56 rounded-2xl" />
        <Skeleton className="h-56 rounded-2xl" />
      </div>
    </div>
  );
}
