import { useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { Navigate, useLocation } from 'react-router-dom'
import { Button } from '../components/ui/Button'
import ErrorBanner from '../components/ui/ErrorBanner'
import Field from '../components/ui/Field'
import Icon from '../components/ui/Icon'
import { INPUT_CLASSES } from '../components/ui/inputStyles'
import { connect, selectIsAuthenticated } from '../features/auth/authSlice'
import { PATHS } from '../routes/paths'

export default function ConnectPage() {
  const dispatch = useDispatch()
  const location = useLocation()
  const isAuthenticated = useSelector(selectIsAuthenticated)
  const { status, error, sessionExpired } = useSelector((state) => state.auth)
  const [key, setKey] = useState('')

  // Once connected (or if already connected), go where the user was heading.
  if (isAuthenticated) {
    return <Navigate to={location.state?.from || PATHS.app} replace />
  }

  function handleSubmit(event) {
    event.preventDefault()
    dispatch(connect(key))
  }

  return (
    <div className="bg-gradient-to-b from-indigo-50/60 to-white px-4 py-16 sm:py-24">
      <div className="mx-auto max-w-md">
        <div className="text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-600 text-white">
            <Icon name="key" className="h-6 w-6" />
          </div>
          <h1 className="mt-6 text-2xl font-semibold tracking-tight text-slate-900">
            Connect your API key
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            The key is checked with the API and kept only for this browser tab.
          </p>
        </div>

        <div className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
          {sessionExpired ? (
            <div className="mb-5 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
              Your key was refused by the API. Please connect again.
            </div>
          ) : null}
          <form onSubmit={handleSubmit} className="space-y-5" noValidate>
            <Field
              id="api-key"
              label="API key"
              hint={
                <>
                  Create one on the server with{' '}
                  <code className="rounded bg-slate-100 px-1">auditor create-api-key NAME</code>.
                </>
              }
            >
              <input
                id="api-key"
                type="password"
                autoComplete="off"
                spellCheck={false}
                placeholder="baa_…"
                value={key}
                onChange={(event) => setKey(event.target.value)}
                className={INPUT_CLASSES}
                aria-invalid={status === 'failed' || undefined}
                required
              />
            </Field>
            <ErrorBanner error={status === 'failed' ? error : null} title="Could not connect" />
            <Button type="submit" className="w-full" loading={status === 'loading'} disabled={!key.trim()}>
              Connect
            </Button>
          </form>
        </div>
      </div>
    </div>
  )
}
