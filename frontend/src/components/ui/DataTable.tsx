import type { ReactNode } from "react";
import { EmptyState } from "./EmptyState";

export interface DataTableColumn<T> {
  key: string;
  header: string;
  render?: (row: T) => ReactNode;
}

export interface DataTableProps<T> {
  columns: DataTableColumn<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  isLoading?: boolean;
  /** Full-table failure — nothing loaded. */
  errorText?: string;
  onRetry?: () => void;
  emptyTitle?: string;
  emptyDescription?: string;
  emptyActionLabel?: string;
  onEmptyAction?: () => void;
  emptyIcon?: ReactNode;
  /** Partial/degraded state: flag individual rows that failed without dropping the rest. */
  rowError?: (row: T) => string | undefined;
  /** Makes the whole row clickable (not just whatever a column happens to
   * render as a link/button) — e.g. opening a detail view. A column that
   * needs its own click target (a resume link, an action button) should
   * stop propagation itself so it doesn't also trigger this. */
  onRowClick?: (row: T) => void;
}

export function DataTable<T>({
  columns,
  rows,
  rowKey,
  isLoading = false,
  errorText,
  onRetry,
  emptyTitle = "Nothing here yet",
  emptyDescription,
  emptyActionLabel,
  onEmptyAction,
  emptyIcon,
  rowError,
  onRowClick,
}: DataTableProps<T>) {
  if (errorText && rows.length === 0) {
    return (
      <EmptyState
        variant="error"
        title="Couldn't load this table"
        description={errorText}
        actionLabel={onRetry ? "Retry" : undefined}
        onAction={onRetry}
      />
    );
  }

  if (!isLoading && rows.length === 0) {
    return (
      <EmptyState
        title={emptyTitle}
        description={emptyDescription}
        actionLabel={emptyActionLabel}
        onAction={onEmptyAction}
        icon={emptyIcon}
      />
    );
  }

  return (
    <div className="overflow-x-auto rounded-card border border-border">
      <table className="w-full text-table text-ink">
        <thead className="sticky top-0 bg-surface border-b border-border">
          <tr>
            {columns.map((col) => (
              <th
                key={col.key}
                className="text-left px-4 py-3 font-semibold text-muted"
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {isLoading
            ? Array.from({ length: 5 }).map((_, i) => (
                <tr key={i} className="border-b border-border last:border-0">
                  {columns.map((col) => (
                    <td key={col.key} className="px-4 py-3">
                      <div className="h-4 w-full rounded-sm bg-border animate-pulse" />
                    </td>
                  ))}
                </tr>
              ))
            : rows.map((row) => {
                const failure = rowError?.(row);
                return (
                  <tr
                    key={rowKey(row)}
                    onClick={onRowClick ? () => onRowClick(row) : undefined}
                    role={onRowClick ? "button" : undefined}
                    tabIndex={onRowClick ? 0 : undefined}
                    onKeyDown={
                      onRowClick
                        ? (e) => {
                            if (e.key === "Enter" || e.key === " ") {
                              e.preventDefault();
                              onRowClick(row);
                            }
                          }
                        : undefined
                    }
                    className={[
                      "border-b border-border last:border-0 hover:bg-primary-soft",
                      onRowClick ? "cursor-pointer" : "",
                    ].join(" ")}
                  >
                    {columns.map((col, i) => (
                      <td key={col.key} className="px-4 py-3">
                        {i === 0 && failure ? (
                          <span className="text-error text-helper block mb-1">
                            {failure}
                          </span>
                        ) : null}
                        {col.render
                          ? col.render(row)
                          : String(
                              (row as Record<string, unknown>)[col.key] ?? "",
                            )}
                      </td>
                    ))}
                  </tr>
                );
              })}
        </tbody>
      </table>
    </div>
  );
}
