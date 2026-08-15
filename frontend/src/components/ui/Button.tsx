import type { ButtonHTMLAttributes, ReactNode } from "react";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "destructive";

const variantClasses: Record<ButtonVariant, string> = {
  primary: "bg-primary text-white hover:bg-primary/90",
  secondary: "bg-surface text-navy border border-border hover:bg-primary-soft",
  ghost: "bg-transparent text-muted hover:bg-primary-soft",
  destructive: "bg-error text-white hover:bg-error/90",
};

/**
 * Shared button visual style, exposed so a `<Link>`/`<a>` styled as a CTA
 * (e.g. the homepage hero) can match `<Button>` exactly without nesting an
 * interactive element inside a `<button>`.
 */
export function buttonClassName({
  variant = "primary",
  hasError = false,
  className = "",
}: {
  variant?: ButtonVariant;
  hasError?: boolean;
  className?: string;
} = {}): string {
  return [
    "inline-flex items-center justify-center gap-2 rounded-control px-5 py-3 text-body font-semibold transition-colors",
    "disabled:opacity-50 disabled:cursor-not-allowed",
    hasError ? "ring-2 ring-error ring-offset-1" : "",
    variantClasses[variant],
    className,
  ].join(" ");
}

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  isLoading?: boolean;
  /** Last attempt failed — shows an error ring without blocking a retry. */
  hasError?: boolean;
  children: ReactNode;
}

export function Button({
  variant = "primary",
  isLoading = false,
  hasError = false,
  disabled,
  className = "",
  children,
  ...rest
}: ButtonProps) {
  return (
    <button
      type="button"
      disabled={disabled || isLoading}
      aria-busy={isLoading}
      className={buttonClassName({ variant, hasError, className })}
      {...rest}
    >
      {isLoading && (
        <span
          className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent"
          aria-hidden="true"
        />
      )}
      {children}
    </button>
  );
}
