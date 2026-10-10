import { forwardRef, useId, type InputHTMLAttributes } from "react";

export interface CheckboxProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, "type"> {
  label?: string;
}

/** design.md § Component Naming Conventions calls for "Checkbox selection for
 * bulk actions" but no primitive existed yet (TS-12 replaced one unstyled
 * instance; TS-17 is its proper home). Unlabeled usage (e.g. a card-header
 * selection toggle) must still pass aria-label. */
export const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(
  function Checkbox({ label, id, className = "", ...rest }, ref) {
    const generatedId = useId();
    const checkboxId = id ?? generatedId;

    const input = (
      <input
        ref={ref}
        type="checkbox"
        id={checkboxId}
        className={[
          "h-5 w-5 rounded-sm border border-border text-primary accent-primary",
          "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary",
          "disabled:cursor-not-allowed disabled:opacity-40",
          className,
        ].join(" ")}
        {...rest}
      />
    );

    if (!label) return input;

    return (
      <label
        htmlFor={checkboxId}
        className="flex items-center gap-2 text-body text-ink"
      >
        {input}
        {label}
      </label>
    );
  },
);
