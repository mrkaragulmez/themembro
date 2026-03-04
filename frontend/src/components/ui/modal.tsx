/**
 * frontend/src/components/ui/modal.tsx
 * Faz 6 — Base Modal bileşeni
 * Framer Motion AnimatePresence ile açılma/kapanma animasyonu.
 * size: "sm" | "md" | "lg" | "fullscreen"
 */

"use client";

import { useEffect, useCallback } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { X } from "lucide-react";
import { clsx } from "clsx";

export type ModalSize = "sm" | "md" | "lg" | "fullscreen";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  size?: ModalSize;
  children: React.ReactNode;
  className?: string;
  /** Modal'ı backdrop tıklamasıyla kapatma */
  closeOnBackdrop?: boolean;
}

const sizeClasses: Record<ModalSize, string> = {
  sm:         "max-w-sm w-full",
  md:         "max-w-[480px] w-full",
  lg:         "max-w-3xl w-full",
  fullscreen: "w-[90vw] max-w-[1200px] h-[85vh]",
};

const backdropVariants = {
  hidden:  { opacity: 0 },
  visible: { opacity: 1 },
};

const panelVariants = {
  hidden:  { opacity: 0, scale: 0.97, y: 8 },
  visible: { opacity: 1, scale: 1, y: 0 },
  exit:    { opacity: 0, scale: 0.97, y: 8 },
};

export function Modal({
  open,
  onClose,
  title,
  size = "md",
  children,
  className,
  closeOnBackdrop = true,
}: ModalProps) {
  // Escape tuşuyla kapat
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    },
    [onClose]
  );

  useEffect(() => {
    if (open) {
      document.addEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "hidden";
    }
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "";
    };
  }, [open, handleKeyDown]);

  return (
    <AnimatePresence>
      {open && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center"
          role="dialog"
          aria-modal="true"
          aria-label={title}
        >
          {/* Backdrop */}
          <motion.div
            className="absolute inset-0 bg-brand-navy/40 backdrop-blur-sm"
            variants={backdropVariants}
            initial="hidden"
            animate="visible"
            exit="hidden"
            transition={{ duration: 0.18 }}
            onClick={closeOnBackdrop ? onClose : undefined}
          />

          {/* Panel */}
          <motion.div
            className={clsx(
              "relative z-10 bg-surface-0 border border-border-default",
              "rounded-2xl shadow-[0_20px_60px_rgba(24,9,66,0.18)]",
              "flex flex-col",
              sizeClasses[size],
              size !== "fullscreen" && "mx-4",
              className
            )}
            variants={panelVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            transition={{ type: "spring", stiffness: 320, damping: 32 }}
          >
            {/* Header */}
            {title && (
              <div className="flex items-center justify-between px-6 py-4 border-b border-border-default shrink-0">
                <h2 className="text-base font-semibold text-text-primary">{title}</h2>
                <button
                  onClick={onClose}
                  className="p-1.5 rounded-lg text-text-tertiary hover:text-text-primary hover:bg-surface-50 transition-colors"
                  aria-label="Kapat"
                >
                  <X size={16} />
                </button>
              </div>
            )}

            {/* Başlık yoksa kapatma butonu sağ üste */}
            {!title && (
              <button
                onClick={onClose}
                className="absolute top-4 right-4 p-1.5 rounded-lg text-text-tertiary hover:text-text-primary hover:bg-surface-50 transition-colors z-10"
                aria-label="Kapat"
              >
                <X size={16} />
              </button>
            )}

            {/* Content */}
            <div className="flex-1 overflow-auto">{children}</div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
