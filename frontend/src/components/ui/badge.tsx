/**
 * frontend/src/components/ui/badge.tsx
 * Faz 6 — Badge / StatusBadge atom bileşeni
 */

import { clsx } from "clsx";

export type BadgeVariant = "default" | "success" | "warning" | "error" | "info" | "outline";

interface BadgeProps {
  variant?: BadgeVariant;
  label: string;
  dot?: boolean;
  className?: string;
}

const variantClasses: Record<BadgeVariant, string> = {
  default:  "bg-surface-100 text-text-secondary",
  success:  "bg-success/15 text-[#1a6b3c]",
  warning:  "bg-warning/15 text-[#92600a]",
  error:    "bg-error/15 text-error",
  info:     "bg-info/15 text-info",
  outline:  "border border-border-default bg-transparent text-text-secondary",
};

const dotClasses: Record<BadgeVariant, string> = {
  default:  "bg-text-tertiary",
  success:  "bg-success",
  warning:  "bg-warning",
  error:    "bg-error",
  info:     "bg-info",
  outline:  "bg-text-tertiary",
};

export function Badge({ variant = "default", label, dot = false, className }: BadgeProps) {
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full",
        "text-xs font-medium",
        variantClasses[variant],
        className
      )}
    >
      {dot && (
        <span
          className={clsx("w-1.5 h-1.5 rounded-full shrink-0", dotClasses[variant])}
          aria-hidden="true"
        />
      )}
      {label}
    </span>
  );
}

// ─── MembroStatusBadge ─────────────────────────────────────────────────────

import type { MembroStatus } from "@/types";

const statusConfig: Record<MembroStatus, { variant: BadgeVariant; label: string }> = {
  active:   { variant: "success",  label: "Aktif" },
  inactive: { variant: "default",  label: "Pasif" },
  archived: { variant: "outline",  label: "Arşivlendi" },
};

export function MembroStatusBadge({ status }: { status: MembroStatus }) {
  const config = statusConfig[status];
  return <Badge variant={config.variant} label={config.label} dot />;
}
