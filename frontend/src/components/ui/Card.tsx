import type { HTMLAttributes, ReactNode } from "react";

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  title?: string;
  isLoading?: boolean;
  errorText?: string;
  disabled?: boolean;
  children?: ReactNode;
}

export function Card({
  title,
  isLoading = false,
  errorText,
  disabled = false,
  className = "",
  children,
  ...rest
}: CardProps) {
  return (
    <div
      className={[
        "rounded-card border border-border bg-surface p-6 shadow-card",
        disabled ? "opacity-50" : "",
        className,
      ].join(" ")}
      aria-busy={isLoading}
      {...rest}
    >
      {isLoading ? (
        <div className="flex flex-col gap-3">
          <div className="h-5 w-1/3 rounded-sm bg-border animate-pulse" />
          <div className="h-4 w-full rounded-sm bg-border animate-pulse" />
          <div className="h-4 w-2/3 rounded-sm bg-border animate-pulse" />
        </div>
      ) : errorText ? (
        <p className="text-body text-error">{errorText}</p>
      ) : (
        <>
          {title && (
            <h3 className="text-card font-semibold text-ink mb-2">{title}</h3>
          )}
          {children}
        </>
      )}
    </div>
  );
}
