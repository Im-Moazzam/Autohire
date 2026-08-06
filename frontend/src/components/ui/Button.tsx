import type { ButtonHTMLAttributes, ReactNode } from 'react'

type Variant = 'primary' | 'secondary' | 'ghost' | 'destructive'

const variantClasses: Record<Variant, string> = {
  primary: 'bg-primary text-white hover:bg-primary/90',
  secondary: 'bg-surface text-navy border border-border hover:bg-primary-soft',
  ghost: 'bg-transparent text-muted hover:bg-primary-soft',
  destructive: 'bg-error text-white hover:bg-error/90',
}

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  isLoading?: boolean
  /** Last attempt failed — shows an error ring without blocking a retry. */
  hasError?: boolean
  children: ReactNode
}

export function Button({
  variant = 'primary',
  isLoading = false,
  hasError = false,
  disabled,
  className = '',
  children,
  ...rest
}: ButtonProps) {
  return (
    <button
      type="button"
      disabled={disabled || isLoading}
      aria-busy={isLoading}
      className={[
        'inline-flex items-center justify-center gap-2 rounded-control px-5 py-3 text-body font-semibold transition-colors',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        hasError ? 'ring-2 ring-error ring-offset-1' : '',
        variantClasses[variant],
        className,
      ].join(' ')}
      {...rest}
    >
      {isLoading && (
        <span
          className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent"
          aria-hidden="true"
        />
      )}
      {children}
    </button>
  )
}
