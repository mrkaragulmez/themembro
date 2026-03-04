/**
 * frontend/src/components/ui/toast.tsx
 * Faz 6.2 — Toast bildirim sistemi
 * Zustand store tabanlı, Framer Motion animasyonlu
 */

"use client";

import { create } from "zustand";
import { useEffect } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle2, XCircle, AlertCircle, Info, X } from "lucide-react";
import { clsx } from "clsx";

// ─── Store ────────────────────────────────────────────────────────────────────

export type ToastType = "success" | "error" | "warning" | "info";

export interface Toast {
  id: string;
  type: ToastType;
  message: string;
  duration?: number; // ms, default 4000
}

interface ToastStore {
  toasts: Toast[];
  add: (toast: Omit<Toast, "id">) => void;
  remove: (id: string) => void;
}

export const useToastStore = create<ToastStore>((set) => ({
  toasts: [],
  add: (t) =>
    set((s) => ({
      toasts: [
        ...s.toasts,
        { ...t, id: `${Date.now()}-${Math.random().toString(36).slice(2)}` },
      ],
    })),
  remove: (id) =>
    set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
}));

// ─── Kısa-yol hook'ları ───────────────────────────────────────────────────────

export function useToast() {
  const { add } = useToastStore();
  return {
    success: (message: string, duration?: number) =>
      add({ type: "success", message, duration }),
    error: (message: string, duration?: number) =>
      add({ type: "error", message, duration }),
    warning: (message: string, duration?: number) =>
      add({ type: "warning", message, duration }),
    info: (message: string, duration?: number) =>
      add({ type: "info", message, duration }),
  };
}

// ─── Tek Toast bileşeni ───────────────────────────────────────────────────────

const ICONS: Record<ToastType, React.ReactNode> = {
  success: <CheckCircle2 size={16} className="text-success shrink-0" />,
  error:   <XCircle     size={16} className="text-error shrink-0" />,
  warning: <AlertCircle size={16} className="text-warning shrink-0" />,
  info:    <Info        size={16} className="text-info shrink-0" />,
};

const BG: Record<ToastType, string> = {
  success: "bg-success/8 border-success/20",
  error:   "bg-error/8 border-error/20",
  warning: "bg-warning/8 border-warning/20",
  info:    "bg-info/8 border-info/20",
};

function ToastItem({ toast }: { toast: Toast }) {
  const remove = useToastStore((s) => s.remove);
  const duration = toast.duration ?? 4000;

  // Otomatik kapan
  useEffect(() => {
    const t = setTimeout(() => remove(toast.id), duration);
    return () => clearTimeout(t);
  }, [toast.id, duration, remove]);

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -8, scale: 0.95 }}
      transition={{ type: "spring", stiffness: 380, damping: 30 }}
      className={clsx(
        "flex items-start gap-2.5 px-4 py-3 rounded-2xl border shadow-md",
        "max-w-sm w-full pointer-events-auto text-sm",
        BG[toast.type]
      )}
    >
      {ICONS[toast.type]}
      <span className="flex-1 text-text-primary leading-snug">{toast.message}</span>
      <button
        onClick={() => remove(toast.id)}
        className="mt-0.5 text-text-tertiary hover:text-text-primary transition-colors shrink-0"
        aria-label="Kapat"
      >
        <X size={14} />
      </button>
    </motion.div>
  );
}

// ─── Toaster (layout'a yerleş) ────────────────────────────────────────────────

export function Toaster() {
  const toasts = useToastStore((s) => s.toasts);

  return (
    <div className="fixed bottom-5 right-5 z-[9999] flex flex-col gap-2 items-end pointer-events-none">
      <AnimatePresence mode="popLayout">
        {toasts.map((t) => (
          <ToastItem key={t.id} toast={t} />
        ))}
      </AnimatePresence>
    </div>
  );
}
