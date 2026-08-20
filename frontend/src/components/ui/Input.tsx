import { forwardRef, useId, type InputHTMLAttributes } from "react";

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  helperText?: string;
  errorText?: string;
  /** Async validation in flight (e.g. checking slug availability). */
  isValidating?: boolean;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  {
    label,
    helperText,
    errorText,
    isValidating = false,
    disabled,
    id,
    className = "",
    ...rest
  },
  ref,
) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  const helperId = `${inputId}-helper`;

  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={inputId} className="text-body font-medium text-ink">
        {label}
      </label>
      <div className="relative">
        <input
          ref={ref}
          id={inputId}
          disabled={disabled}
          aria-invalid={!!errorText}
          aria-describedby={helperText || errorText ? helperId : undefined}
          className={[
            "w-full rounded-md border px-3 py-3 text-body text-ink",
            "disabled:bg-canvas disabled:text-muted disabled:cursor-not-allowed",
            errorText ? "border-error" : "border-border",
            className,
          ].join(" ")}
          {...rest}
        />
        {isValidating && (
          <span
            className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 animate-spin rounded-full border-2 border-muted border-t-transparent"
            aria-hidden="true"
          />
        )}
      </div>
      {errorText ? (
        <p id={helperId} className="text-helper text-error">
          {errorText}
        </p>
      ) : helperText ? (
        <p id={helperId} className="text-helper text-muted">
          {helperText}
        </p>
      ) : null}
    </div>
  );
});
