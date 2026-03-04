/**
 * frontend/src/app/(shell)/knowledge/loading.tsx
 * Faz 6.4 — Bilgi Bankası yüklenme ekranı
 */

import { Skeleton } from "@/components/ui/skeleton";

export default function KnowledgeLoading() {
  return (
    <div className="max-w-3xl mx-auto px-6 py-8">
      <div className="flex items-center justify-between mb-6">
        <div className="space-y-1.5">
          <Skeleton className="h-7 w-40" />
          <Skeleton className="h-4 w-24" />
        </div>
        <Skeleton className="h-9 w-36 rounded-xl" />
      </div>
      <div className="space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-16 rounded-xl" />
        ))}
      </div>
    </div>
  );
}
