/**
 * frontend/src/components/ui/button.tsx
 * Faz 6 — Button atom bileşeni
 * Varyantlar: primary | outline | ghost | danger
 * Boyutlar: sm | md | lg
 */

import { forwardRef } from "react";
import { clsx } from "clsx";

export type ButtonVariant = "primary" | "outline" | "ghost" | "danger";
export type ButtonSize = "sm" | "md" | "lg";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  icon?: React.ReactNode;
  iconPosition?: "left" | "right";
}

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    "bg-brand-navy text-surface-0 hover:bg-surface-800 active:bg-surface-900 shadow-sm",
  outline:
    "border border-border-default bg-transparent text-text-primary hover:bg-surface-50 hover:border-border-active active:bg-surface-100",
  ghost:
    "bg-transparent text-text-secondary hover:bg-surface-50 hover:text-text-primary active:bg-surface-100",
  danger:
    "bg-error/10 text-error border border-error/20 hover:bg-error/20 active:bg-error/30",
};

const sizeClasses: Record<ButtonSize, string> = {
  sm: "h-8 px-3 text-xs gap-1.5 rounded-lg",
  md: "h-9 px-4 text-sm gap-2 rounded-xl",
  lg: "h-11 px-5 text-base gap-2.5 rounded-xl",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = "primary",
      size = "md",
      loading = false,
      icon,
      iconPosition = "left",
      className,
      children,
      disabled,
      ...props
    },
    ref
  ) => {
    const isDisabled = disabled || loading;

    return (
      <button
        ref={ref}
        disabled={isDisabled}
        className={clsx(
          // Base
          "inline-flex items-center justify-center font-semibold",
          "transition-all duration-100 ease-out",
          "cursor-pointer select-none",
          "focus-visible:outline-2 focus-visible:outline-brand-periwinkle focus-visible:outline-offset-2",
          // Variant & Size
          variantClasses[variant],
          sizeClasses[size],
          // Disabled
          isDisabled && "opacity-50 cursor-not-allowed pointer-events-none",
          className
        )}
        {...props}
      >
        {loading ? (
          <>
            <span
              className="inline-block w-[1em] h-[1em] rounded-full border-2 border-current border-t-transparent animate-spin"
              aria-hidden="true"
            />
            {children && <span>{children}</span>}
          </>
        ) : (
          <>
            {icon && iconPosition === "left" && (
              <span className="shrink-0" aria-hidden="true">{icon}</span>
            )}
            {children && <span>{children}</span>}
            {icon && iconPosition === "right" && (
              <span className="shrink-0" aria-hidden="true">{icon}</span>
            )}
          </>
        )}
      </button>
    );
  }
);

Button.displayName = "Button";
