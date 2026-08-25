import { useEffect, useRef, type ReactNode } from "react";
import { Button } from "./Button";

export interface ModalProps {
  open: boolean;
  title: string;
  onClose: () => void;
  children?: ReactNode;
  primaryLabel?: string;
  onPrimary?: () => void;
  isLoading?: boolean;
  errorText?: string;
  /** Wider variant for content-heavy modals (e.g. a full candidate profile). */
  size?: "md" | "lg";
  /** Custom footer (e.g. a dynamic set of status-change buttons) — takes
   * over the fixed footer area instead of the Cancel/primaryLabel pair.
   * Stays pinned below the scrollable body, same as the Cancel/primary
   * footer, so it's never scrolled out of view. */
  footer?: ReactNode;
}

function CloseIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <path d="M18 6 6 18M6 6l12 12" />
    </svg>
  );
}

const sizeClasses = {
  md: "max-w-md",
  lg: "max-w-2xl",
};

export function Modal({
  open,
  title,
  onClose,
  children,
  primaryLabel,
  onPrimary,
  isLoading = false,
  errorText,
  size = "md",
  footer,
}: ModalProps) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  // showModal() doesn't lock body scroll on its own — without this the page
  // behind the modal still scrolls (and its own scrollbar stays visible)
  // while the dialog is open.
  useEffect(() => {
    if (!open) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, [open]);

  return (
    <dialog
      ref={ref}
      onClose={onClose}
      onCancel={onClose}
      onClick={(e) => {
        // Click on the backdrop (the ::backdrop pseudo-element isn't a real
        // child, so a click landing directly on <dialog> itself is the backdrop).
        if (e.target === ref.current) onClose();
      }}
      className={[
        "fixed inset-0 m-auto max-h-[85vh] w-[calc(100%-2rem)] overflow-hidden rounded-card p-0",
        "shadow-modal backdrop:bg-navy/50 backdrop:backdrop-blur-[2px]",
        sizeClasses[size],
      ].join(" ")}
    >
      {/* max-h/flex-col here (not just on <dialog>) so the header and footer
       * stay put and only the body scrolls — a <dialog> can't apply
       * min-height:0 to a non-flex child, which is what lets the middle
       * flex item shrink and become the one scrollable region. */}
      <div className="flex max-h-[85vh] flex-col animate-slide-up">
        <div className="flex shrink-0 items-center justify-between gap-4 border-b border-border px-6 py-5">
          <h2 className="text-card font-semibold text-ink">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            title="Close"
            aria-label="Close"
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-muted transition-colors hover:bg-primary-soft hover:text-ink"
          >
            <CloseIcon className="h-5 w-5" />
          </button>
        </div>

        <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-6 py-6">
          {errorText && <p className="text-body text-error">{errorText}</p>}
          {children}
        </div>

        {footer ? (
          <div className="shrink-0 border-t border-border px-6 py-4">
            {footer}
          </div>
        ) : (
          primaryLabel &&
          onPrimary && (
            <div className="flex shrink-0 justify-end gap-3 border-t border-border px-6 py-4">
              <Button
                variant="secondary"
                onClick={onClose}
                disabled={isLoading}
              >
                Cancel
              </Button>
              <Button onClick={onPrimary} isLoading={isLoading}>
                {primaryLabel}
              </Button>
            </div>
          )
        )}
      </div>
    </dialog>
  );
}
