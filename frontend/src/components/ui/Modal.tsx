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
}

export function Modal({
  open,
  title,
  onClose,
  children,
  primaryLabel,
  onPrimary,
  isLoading = false,
  errorText,
}: ModalProps) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog
      ref={ref}
      onClose={onClose}
      onCancel={onClose}
      className="rounded-card p-0 shadow-modal backdrop:bg-navy/40 w-full max-w-md"
    >
      <div className="p-6 flex flex-col gap-4">
        <h2 className="text-card font-semibold text-ink">{title}</h2>
        {errorText && <p className="text-body text-error">{errorText}</p>}
        {children}
        <div className="flex justify-end gap-3 mt-2">
          <Button variant="secondary" onClick={onClose} disabled={isLoading}>
            Cancel
          </Button>
          {primaryLabel && onPrimary && (
            <Button onClick={onPrimary} isLoading={isLoading}>
              {primaryLabel}
            </Button>
          )}
        </div>
      </div>
    </dialog>
  );
}
