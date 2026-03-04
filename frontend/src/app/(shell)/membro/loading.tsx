/**
 * frontend/src/app/(shell)/membro/loading.tsx
 * Faz 6.4 — Membro listesi yüklenme ekranı
 */

import { Skeleton } from "@/components/ui/skeleton";

export default function MembroLoading() {
  return (
    <div className="max-w-5xl mx-auto px-6 py-8">
      <div className="flex items-center justify-between mb-6">
        <Skeleton className="h-8 w-40" />
        <Skeleton className="h-9 w-36 rounded-xl" />
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="h-44 rounded-2xl" />
        ))}
      </div>
    </div>
  );
}
