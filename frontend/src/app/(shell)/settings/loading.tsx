/**
 * frontend/src/app/(shell)/settings/loading.tsx
 * Faz 6.5 — Ayarlar yüklenme ekranı
 */

import { Skeleton } from "@/components/ui/skeleton";

export default function SettingsLoading() {
  return (
    <div className="max-w-2xl mx-auto px-6 py-8">
      <Skeleton className="h-8 w-32 mb-2" />
      <Skeleton className="h-4 w-56 mb-8" />
      <div className="rounded-2xl border border-border-default overflow-hidden">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="px-6 py-5 border-b border-border-default last:border-0 space-y-3">
            <Skeleton className="h-4 w-28" />
            <div className="flex gap-3 items-center">
              <Skeleton className="h-8 w-8 rounded-xl" />
              <div className="space-y-1.5">
                <Skeleton className="h-3 w-20" />
                <Skeleton className="h-3 w-32" />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
