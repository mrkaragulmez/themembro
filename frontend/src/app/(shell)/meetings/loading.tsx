/**
 * frontend/src/app/(shell)/meetings/loading.tsx
 * Faz 6.4 — Toplantılar yüklenme ekranı
 */

import { Skeleton } from "@/components/ui/skeleton";

export default function MeetingsLoading() {
  return (
    <div className="max-w-3xl mx-auto px-6 py-8">
      <div className="flex items-center justify-between mb-6">
        <div className="space-y-1.5">
          <Skeleton className="h-7 w-36" />
          <Skeleton className="h-4 w-28" />
        </div>
        <Skeleton className="h-9 w-40 rounded-xl" />
      </div>
      <div className="space-y-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-20 rounded-2xl" />
        ))}
      </div>
    </div>
  );
}
