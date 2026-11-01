import { Link } from 'react-router-dom'
import { buttonClasses } from './buttonStyles'
import Spinner from './Spinner'

export function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  className = '',
  children,
  type = 'button',
  disabled,
  ...props
}) {
  return (
    <button
      type={type}
      className={buttonClasses(variant, size, className)}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? <Spinner className="h-4 w-4" /> : null}
      {children}
    </button>
  )
}

/** A router link styled as a button. */
export function ButtonLink({ variant = 'primary', size = 'md', className = '', ...props }) {
  return <Link className={buttonClasses(variant, size, className)} {...props} />
}
