import {
  createContext,
  useCallback,
  useContext,
  useState,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";

type Variant = "success" | "error" | "warning" | "loading";

interface ToastItem {
  id: number;
  message: string;
  variant: Variant;
}

const variantClasses: Record<Variant, string> = {
  success: "bg-success text-white",
  error: "bg-error text-white",
  warning: "bg-warning text-white",
  loading: "bg-navy text-white",
};

interface ToastContextValue {
  showToast: (message: string, variant?: Variant) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within a ToastProvider");
  return ctx;
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const showToast = useCallback(
    (message: string, variant: Variant = "success") => {
      const id = Date.now();
      setToasts((prev) => [...prev, { id, message, variant }]);
      if (variant !== "loading") {
        setTimeout(
          () => setToasts((prev) => prev.filter((t) => t.id !== id)),
          4000,
        );
      }
    },
    [],
  );

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      {createPortal(
        <div className="fixed bottom-6 right-6 flex flex-col gap-2 z-50">
          {toasts.map((t) => (
            <div
              key={t.id}
              role="status"
              className={[
                "flex items-center gap-2 rounded-control px-4 py-3 text-body shadow-modal",
                variantClasses[t.variant],
              ].join(" ")}
            >
              {t.variant === "loading" && (
                <span
                  className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent"
                  aria-hidden="true"
                />
              )}
              {t.message}
            </div>
          ))}
        </div>,
        document.body,
      )}
    </ToastContext.Provider>
  );
}
