/**
 * frontend/src/components/ui/spinner.tsx
 * Faz 6 — Loading spinner bileşeni
 */

import { clsx } from "clsx";

interface SpinnerProps {
  size?: "sm" | "md" | "lg";
  className?: string;
  label?: string;
}

const sizeMap = {
  sm: "w-4 h-4 border-[1.5px]",
  md: "w-6 h-6 border-2",
  lg: "w-8 h-8 border-2",
};

export function Spinner({ size = "md", className, label = "Yükleniyor…" }: SpinnerProps) {
  return (
    <span
      role="status"
      aria-label={label}
      className={clsx("inline-flex items-center justify-center", className)}
    >
      <span
        className={clsx(
          "rounded-full border-brand-periwinkle border-t-transparent animate-spin",
          sizeMap[size]
        )}
        aria-hidden="true"
      />
    </span>
  );
}

// ─── Tam ekran / merkez loading ───────────────────────────────────────────────

export function PageSpinner() {
  return (
    <div className="flex items-center justify-center min-h-[200px]">
      <Spinner size="lg" />
    </div>
  );
}
