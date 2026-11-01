import { Button } from './Button'
import Icon from './Icon'

/**
 * Shows an API error payload {status, code, message}. The message comes from the API's
 * error body, so it is the same text a curl user would see.
 */
export default function ErrorBanner({ error, title = 'Something went wrong', onRetry, children }) {
  if (!error) return null
  return (
    <div role="alert" className="rounded-lg border border-rose-200 bg-rose-50 p-4">
      <div className="flex gap-3">
        <Icon name="alert" className="mt-0.5 h-5 w-5 flex-none text-rose-600" />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-rose-800">{title}</p>
          <p className="mt-1 text-sm text-rose-700">{error.message}</p>
          {error.code || error.status ? (
            <p className="mt-1 font-mono text-xs text-rose-600">
              {error.status ? `HTTP ${error.status}` : null}
              {error.status && error.code ? ' · ' : null}
              {error.code}
            </p>
          ) : null}
          {children ? <div className="mt-3">{children}</div> : null}
        </div>
        {onRetry ? (
          <Button variant="secondary" size="sm" onClick={onRetry}>
            <Icon name="refresh" className="h-4 w-4" />
            Retry
          </Button>
        ) : null}
      </div>
    </div>
  )
}
