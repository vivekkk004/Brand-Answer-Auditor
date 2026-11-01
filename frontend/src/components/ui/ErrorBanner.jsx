import Alert from './Alert'
import { Button } from './Button'
import Icon from './Icon'

/**
 * Shows an API error payload {status, code, message}. The message comes from the API's
 * error body, so it is the same text a curl user would see.
 */
export default function ErrorBanner({ error, title = 'Something went wrong', onRetry, children }) {
  if (!error) return null
  return (
    <Alert
      tone="danger"
      role="alert"
      title={title}
      action={
        onRetry ? (
          <Button variant="secondary" size="sm" onClick={onRetry}>
            <Icon name="refresh" className="h-4 w-4" />
            Retry
          </Button>
        ) : null
      }
    >
      <p>{error.message}</p>
      {error.code || error.status ? (
        <p className="mt-1 font-mono text-xs text-rose-600">
          {error.status ? `HTTP ${error.status}` : null}
          {error.status && error.code ? ' · ' : null}
          {error.code}
        </p>
      ) : null}
      {children ? <div className="mt-3">{children}</div> : null}
    </Alert>
  )
}
