import type { ReactNode } from "react";
import { Button } from "./Button";

export interface EmptyStateProps {
  /** 'error' reuses the same layout for the error state — same shape, red tone. */
  variant?: "empty" | "error";
  title: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
  icon?: ReactNode;
}

export function EmptyState({
  variant = "empty",
  title,
  description,
  actionLabel,
  onAction,
  icon,
}: EmptyStateProps) {
  const isError = variant === "error";

  return (
    <div className="flex flex-col items-center gap-3 text-center py-12 px-6">
      {icon ?? (
        <div
          className={[
            "h-10 w-10 rounded-full flex items-center justify-center text-body font-semibold",
            isError ? "bg-error/10 text-error" : "bg-primary-soft text-primary",
          ].join(" ")}
          aria-hidden="true"
        >
          {isError ? "!" : "·"}
        </div>
      )}
      <h3 className="text-card font-semibold text-ink">{title}</h3>
      {description && (
        <p className="text-body text-muted max-w-sm">{description}</p>
      )}
      {actionLabel && onAction && (
        <Button
          variant={isError ? "secondary" : "primary"}
          onClick={onAction}
          className="mt-2"
        >
          {actionLabel}
        </Button>
      )}
    </div>
  );
}
