import { forwardRef, useId, type TextareaHTMLAttributes } from "react";

export interface TextareaProps
  extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label: string;
  helperText?: string;
  errorText?: string;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  function Textarea(
    { label, helperText, errorText, disabled, id, className = "", ...rest },
    ref,
  ) {
    const generatedId = useId();
    const textareaId = id ?? generatedId;
    const helperId = `${textareaId}-helper`;

    return (
      <div className="flex flex-col gap-2">
        <label htmlFor={textareaId} className="text-body font-medium text-ink">
          {label}
        </label>
        <textarea
          ref={ref}
          id={textareaId}
          disabled={disabled}
          aria-invalid={!!errorText}
          aria-describedby={helperText || errorText ? helperId : undefined}
          rows={4}
          className={[
            "w-full rounded-md border px-3 py-3 text-body text-ink",
            "disabled:bg-canvas disabled:text-muted disabled:cursor-not-allowed",
            errorText ? "border-error" : "border-border",
            className,
          ].join(" ")}
          {...rest}
        />
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
