/**
 * frontend/src/components/ui/input.tsx
 * Faz 6 — Input ve Textarea atom bileşeni
 */

import { forwardRef } from "react";
import { clsx } from "clsx";

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  hint?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, hint, className, id, ...props }, ref) => {
    const inputId = id ?? label?.toLowerCase().replace(/\s+/g, "-");

    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label htmlFor={inputId} className="text-sm font-medium text-text-primary">
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={inputId}
          className={clsx(
            "w-full h-9 px-3 rounded-xl border text-sm text-text-primary",
            "bg-surface-0 placeholder:text-text-tertiary",
            "transition-colors duration-100",
            error
              ? "border-error focus:border-error focus:ring-2 focus:ring-error/20"
              : "border-border-default hover:border-border-active focus:border-brand-periwinkle focus:ring-2 focus:ring-brand-periwinkle/15",
            "outline-none",
            className
          )}
          {...props}
        />
        {error && <p className="text-xs text-error">{error}</p>}
        {hint && !error && <p className="text-xs text-text-tertiary">{hint}</p>}
      </div>
    );
  }
);

Input.displayName = "Input";

// ─── Textarea ─────────────────────────────────────────────────────────────────

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  hint?: string;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ label, error, hint, className, id, rows = 4, ...props }, ref) => {
    const inputId = id ?? label?.toLowerCase().replace(/\s+/g, "-");

    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label htmlFor={inputId} className="text-sm font-medium text-text-primary">
            {label}
          </label>
        )}
        <textarea
          ref={ref}
          id={inputId}
          rows={rows}
          className={clsx(
            "w-full px-3 py-2 rounded-xl border text-sm text-text-primary",
            "bg-surface-0 placeholder:text-text-tertiary resize-none",
            "transition-colors duration-100",
            error
              ? "border-error focus:border-error focus:ring-2 focus:ring-error/20"
              : "border-border-default hover:border-border-active focus:border-brand-periwinkle focus:ring-2 focus:ring-brand-periwinkle/15",
            "outline-none",
            className
          )}
          {...props}
        />
        {error && <p className="text-xs text-error">{error}</p>}
        {hint && !error && <p className="text-xs text-text-tertiary">{hint}</p>}
      </div>
    );
  }
);

Textarea.displayName = "Textarea";
