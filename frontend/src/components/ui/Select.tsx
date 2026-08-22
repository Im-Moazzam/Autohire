import { forwardRef, useId, type SelectHTMLAttributes } from "react";

export interface SelectOption {
  value: string;
  label: string;
}

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string;
  options: SelectOption[];
  helperText?: string;
  errorText?: string;
  isLoading?: boolean;
  placeholder?: string;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  function Select(
    {
      label,
      options,
      helperText,
      errorText,
      isLoading = false,
      placeholder,
      disabled,
      id,
      className = "",
      ...rest
    },
    ref,
  ) {
    const generatedId = useId();
    const selectId = id ?? generatedId;
    const helperId = `${selectId}-helper`;

    return (
      <div className="flex flex-col gap-2">
        <label htmlFor={selectId} className="text-body font-medium text-ink">
          {label}
        </label>
        <select
          ref={ref}
          id={selectId}
          disabled={disabled || isLoading}
          aria-invalid={!!errorText}
          aria-describedby={helperText || errorText ? helperId : undefined}
          className={[
            "w-full rounded-md border px-3 py-3 text-body text-ink bg-surface",
            "disabled:bg-canvas disabled:text-muted disabled:cursor-not-allowed",
            errorText ? "border-error" : "border-border",
            className,
          ].join(" ")}
          {...rest}
        >
          {isLoading ? (
            <option>Loading…</option>
          ) : (
            <>
              {placeholder && <option value="">{placeholder}</option>}
              {options.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </>
          )}
        </select>
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
  },
);
