import type { InputHTMLAttributes } from 'react'
import { useId } from 'react'

export interface FileInputProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label: string
  helperText?: string
  errorText?: string
  /** 0-100 while an upload is in flight. */
  uploadProgress?: number
}

export function FileInput({
  label,
  helperText,
  errorText,
  uploadProgress,
  disabled,
  id,
  className = '',
  ...rest
}: FileInputProps) {
  const generatedId = useId()
  const inputId = id ?? generatedId
  const helperId = `${inputId}-helper`
  const isUploading = uploadProgress !== undefined && uploadProgress < 100

  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={inputId} className="text-body font-medium text-ink">
        {label}
      </label>
      <input
        id={inputId}
        type="file"
        disabled={disabled || isUploading}
        aria-invalid={!!errorText}
        aria-describedby={helperText || errorText ? helperId : undefined}
        className={[
          'w-full rounded-md border px-3 py-3 text-body text-ink',
          'file:mr-3 file:rounded-control file:border-0 file:bg-primary-soft file:px-3 file:py-2 file:text-primary file:font-medium',
          'disabled:bg-canvas disabled:text-muted disabled:cursor-not-allowed',
          errorText ? 'border-error' : 'border-border',
          className,
        ].join(' ')}
        {...rest}
      />
      {isUploading && (
        <div className="h-2 w-full rounded-sm bg-primary-soft overflow-hidden">
          <div
            className="h-full bg-primary transition-[width]"
            style={{ width: `${uploadProgress}%` }}
          />
        </div>
      )}
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
  )
}
