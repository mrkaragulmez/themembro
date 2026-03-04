/**
 * frontend/src/components/ui/avatar.tsx
 * Faz 6 — Avatar atom bileşeni
 * Initials + renk, opsiyonel image src
 */

import { clsx } from "clsx";

export type AvatarSize = "xs" | "sm" | "md" | "lg" | "xl";

interface AvatarProps {
  name: string;
  color?: string;     // hex renk (MEMBRO_COLORS'dan)
  src?: string;
  size?: AvatarSize;
  className?: string;
}

const sizeClasses: Record<AvatarSize, { wrapper: string; text: string }> = {
  xs: { wrapper: "w-6 h-6",   text: "text-[9px]" },
  sm: { wrapper: "w-8 h-8",   text: "text-[10px]" },
  md: { wrapper: "w-10 h-10", text: "text-xs" },
  lg: { wrapper: "w-12 h-12", text: "text-sm" },
  xl: { wrapper: "w-16 h-16", text: "text-base" },
};

/** İsmin baş harflerini döner — maksimum 2 karakter */
function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

/** Rengin açık mı koyu mu olduğunu belirler (metin rengi seçimi için) */
function isLightColor(hex: string): boolean {
  const h = hex.replace("#", "");
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  // Perceived luminance
  return (0.299 * r + 0.587 * g + 0.114 * b) / 255 > 0.6;
}

export function Avatar({ name, color = "#655F9C", src, size = "md", className }: AvatarProps) {
  const { wrapper, text } = sizeClasses[size];
  const initials = getInitials(name);
  const textColor = isLightColor(color) ? "#180942" : "#FAF9FF";

  return (
    <span
      className={clsx(
        "inline-flex items-center justify-center rounded-full shrink-0 overflow-hidden select-none",
        wrapper,
        className
      )}
      style={{ backgroundColor: color }}
      aria-label={name}
      role="img"
      title={name}
    >
      {src ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={src} alt={name} className="w-full h-full object-cover" />
      ) : (
        <span
          className={clsx("font-black leading-none tracking-tight", text)}
          style={{ color: textColor }}
        >
          {initials}
        </span>
      )}
    </span>
  );
}
