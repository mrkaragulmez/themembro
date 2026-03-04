/**
 * frontend/src/components/ui/skeleton.tsx
 * Faz 6 — Skeleton loading placeholder bileşeni
 */

import { clsx } from "clsx";

interface SkeletonProps {
  className?: string;
  /** Tam genişlik */
  fullWidth?: boolean;
}

export function Skeleton({ className, fullWidth = false }: SkeletonProps) {
  return (
    <span
      aria-hidden="true"
      className={clsx(
        "block bg-surface-100 rounded-xl animate-skeleton",
        fullWidth && "w-full",
        className
      )}
    />
  );
}

// ─── MembroCard Skeleton ──────────────────────────────────────────────────────

export function MembroCardSkeleton() {
  return (
    <div className="rounded-2xl border border-border-default bg-surface-0 p-5 space-y-4">
      <div className="flex items-center gap-3">
        <Skeleton className="w-12 h-12 rounded-full" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-4 w-28" />
          <Skeleton className="h-3 w-16" />
        </div>
      </div>
      <Skeleton className="h-3 w-full" />
      <Skeleton className="h-3 w-3/4" />
      <div className="flex gap-2 pt-1">
        <Skeleton className="h-8 w-24 rounded-xl" />
        <Skeleton className="h-8 w-8 rounded-xl" />
      </div>
    </div>
  );
}

// ─── Sidebar Membro List Skeleton ─────────────────────────────────────────────

export function SidebarMembroSkeleton() {
  return (
    <div className="space-y-1 px-2">
      {[1, 2, 3].map((i) => (
        <div key={i} className="flex items-center gap-2.5 px-2 py-2">
          <Skeleton className="w-6 h-6 rounded-full shrink-0" />
          <Skeleton className="h-3 flex-1 rounded-md" />
        </div>
      ))}
    </div>
  );
}
