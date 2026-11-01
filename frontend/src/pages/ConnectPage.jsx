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

const POINTS = [
  { icon: 'chart', text: 'Inclusion rates with confidence intervals' },
  { icon: 'verify', text: 'Every claim checked against your catalogue' },
  { icon: 'users', text: 'Contradictions confirmed by a person' },
]

export default function ConnectPage() {
  const dispatch = useDispatch()
  const location = useLocation()
  const isAuthenticated = useSelector(selectIsAuthenticated)
  const { status, error, sessionExpired } = useSelector((state) => state.auth)
  const [key, setKey] = useState('')
  const [showKey, setShowKey] = useState(false)

  // Once connected (or if already connected), go where the user was heading.
  if (isAuthenticated) {
    return <Navigate to={location.state?.from || PATHS.app} replace />
  }

  function handleSubmit(event) {
    event.preventDefault()
    dispatch(connect(key))
  }

  return (
    <div className="mx-auto grid max-w-7xl gap-10 px-4 py-12 sm:px-6 lg:grid-cols-2 lg:gap-16 lg:px-8 lg:py-20">
      {/* Brand panel */}
      <div className="relative isolate hidden overflow-hidden rounded-3xl bg-gradient-to-br from-indigo-600 to-violet-600 p-10 text-white shadow-float lg:flex lg:flex-col">
        <div className="bg-grid absolute inset-0 -z-10 opacity-20 invert" />
        <div className="absolute -right-20 -bottom-20 -z-10 h-72 w-72 rounded-full bg-violet-400/40 blur-3xl" />
        <p className="text-sm font-semibold text-indigo-100">Brand Answer Auditor</p>
        <h2 className="mt-4 text-3xl font-bold tracking-tight">
          Audit AI answers with confidence.
        </h2>
        <p className="mt-4 text-indigo-100">
          Connect with your API key to queue audit runs, verify answers and work the review
          queue.
        </p>
        <ul className="mt-10 space-y-4">
          {POINTS.map((point) => (
            <li key={point.text} className="flex items-center gap-3">
              <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-white/15 ring-1 ring-white/20">
                <Icon name={point.icon} className="h-5 w-5" />
              </span>
              <span className="text-[15px] font-medium">{point.text}</span>
            </li>
          ))}
        </ul>
        <div className="mt-auto" />
        <div className="mt-10 rounded-2xl bg-white/10 p-5 ring-1 ring-white/15 backdrop-blur">
          <p className="flex items-center gap-2 text-sm font-semibold">
            <Icon name="shield" className="h-4 w-4" />
            Your key stays private
          </p>
          <p className="mt-1.5 text-sm text-indigo-100">
            It is kept only in this browser tab and cleared when you close it or disconnect.
            The server stores just a hash of it.
          </p>
        </div>
      </div>

      {/* Form */}
      <div className="flex flex-col justify-center">
        <div className="mx-auto w-full max-w-md">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-500 text-white shadow-sm">
            <Icon name="key" className="h-6 w-6" />
          </div>
          <h1 className="mt-6 text-3xl font-bold tracking-tight text-slate-900">
            Connect your API key
          </h1>
          <p className="mt-2 text-[15px] text-slate-500">
            The key is checked with the API and kept only for this browser tab.
          </p>

          {sessionExpired ? (
            <div className="mt-6 flex gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
              <Icon name="alert" className="h-5 w-5 flex-none" />
              Your key was refused by the API. Please connect again.
            </div>
          ) : null}

          <form onSubmit={handleSubmit} className="mt-8 space-y-5" noValidate>
            <Field
              id="api-key"
              label="API key"
              hint={
                <>
                  Create one on the server with{' '}
                  <code className="rounded bg-slate-100 px-1 text-slate-700">
                    auditor create-api-key NAME
                  </code>
                </>
              }
            >
              <div className="relative">
                <input
                  id="api-key"
                  type={showKey ? 'text' : 'password'}
                  autoComplete="off"
                  spellCheck={false}
                  placeholder="baa_…"
                  value={key}
                  onChange={(event) => setKey(event.target.value)}
                  className={`${INPUT_CLASSES} py-2.5 pr-16 font-mono`}
                  aria-invalid={status === 'failed' || undefined}
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowKey((value) => !value)}
                  className="absolute inset-y-0 right-2 my-auto h-7 rounded-md px-2 text-xs font-semibold text-slate-500 hover:bg-slate-100 hover:text-slate-800"
                  aria-label={showKey ? 'Hide key' : 'Show key'}
                >
                  {showKey ? 'Hide' : 'Show'}
                </button>
              </div>
            </Field>
            <ErrorBanner error={status === 'failed' ? error : null} title="Could not connect" />
            <Button
              type="submit"
              size="lg"
              className="w-full"
              loading={status === 'loading'}
              disabled={!key.trim()}
            >
              Connect
            </Button>
          </form>
        </div>
      </div>
    </div>
  )
}
