import { useEffect, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'
import { logout } from '../../features/auth/authSlice'
import { fetchHealth } from '../../features/health/healthSlice'
import { PATHS } from '../../routes/paths'
import { shortId } from '../../utils/format'
import { ButtonLink } from '../ui/Button'
import Icon from '../ui/Icon'
import Logo from '../ui/Logo'

const NAV_ITEMS = [
  { to: PATHS.app, label: 'Overview', icon: 'home', end: true },
  { to: PATHS.runs, label: 'Audit runs', icon: 'runs' },
  { to: PATHS.verify, label: 'Verify answer', icon: 'verify' },
  { to: PATHS.review, label: 'Review queue', icon: 'review' },
]

const HEALTH_STYLE = {
  ok: { dot: 'bg-emerald-500', ring: 'bg-emerald-400', text: 'API connected', pill: 'text-emerald-700 bg-emerald-50 ring-emerald-200' },
  down: { dot: 'bg-rose-500', ring: 'bg-rose-400', text: 'API unavailable', pill: 'text-rose-700 bg-rose-50 ring-rose-200' },
  unknown: { dot: 'bg-slate-400', ring: 'bg-slate-300', text: 'Checking API…', pill: 'text-slate-600 bg-slate-50 ring-slate-200' },
}

/** Breadcrumb labels for the current URL, e.g. ["Audit runs", "e1919b66"]. */
function crumbsFor(pathname) {
  const parts = pathname.replace(/^\/app\/?/, '').split('/').filter(Boolean)
  if (!parts.length) return [{ label: 'Overview' }]
  const [section, id] = parts
  const sections = {
    runs: { label: 'Audit runs', to: PATHS.runs },
    verify: { label: 'Verify answer', to: PATHS.verify },
    answers: { label: 'Answers' },
    review: { label: 'Review queue', to: PATHS.review },
  }
  const first = sections[section] || { label: section }
  if (!id) return [{ label: first.label }]
  return [first, { label: id === 'new' ? 'New run' : shortId(id) }]
}

function HealthDot({ health }) {
  const style = HEALTH_STYLE[health]
  return (
    <span className="relative flex h-2 w-2">
      {health === 'ok' ? (
        <span className={`absolute inline-flex h-full w-full animate-ping rounded-full opacity-60 ${style.ring}`} />
      ) : null}
      <span className={`relative inline-flex h-2 w-2 rounded-full ${style.dot}`} />
    </span>
  )
}

function SidebarContent({ onNavigate }) {
  const dispatch = useDispatch()
  const health = useSelector((state) => state.health.state)
  const apiKey = useSelector((state) => state.auth.apiKey)

  return (
    <div className="flex h-full flex-col">
      <div className="flex h-16 items-center px-5">
        <Logo to={PATHS.app} dark />
      </div>

      <div className="px-3 pt-6">
        <p className="px-3 text-[11px] font-semibold tracking-wider text-indigo-200/50 uppercase">
          Workspace
        </p>
        <nav className="mt-2 space-y-1" aria-label="App">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              onClick={onNavigate}
              className={({ isActive }) =>
                `group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-150 ${
                  isActive
                    ? 'bg-gradient-to-r from-indigo-500/25 to-violet-500/10 text-white ring-1 ring-white/10 ring-inset'
                    : 'text-slate-400 hover:bg-white/5 hover:text-white'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  {isActive ? (
                    <span className="absolute top-2 bottom-2 -left-3 w-1 rounded-r-full bg-gradient-to-b from-indigo-400 to-violet-400 shadow-[0_0_12px_rgb(129_140_248/0.8)]" />
                  ) : null}
                  <Icon
                    name={item.icon}
                    className={`h-5 w-5 transition-colors ${isActive ? 'text-indigo-300' : 'text-slate-500 group-hover:text-slate-300'}`}
                  />
                  {item.label}
                </>
              )}
            </NavLink>
          ))}
        </nav>
      </div>

      <div className="mt-auto p-3">
        <div className="rounded-2xl bg-white/5 p-3.5 ring-1 ring-white/10 ring-inset">
          <div className="flex items-center gap-2 text-xs font-medium text-slate-300">
            <HealthDot health={health} />
            {HEALTH_STYLE[health].text}
          </div>
          {apiKey ? (
            <p className="mt-2 flex items-center gap-1.5 font-mono text-xs text-slate-400">
              <Icon name="key" className="h-3.5 w-3.5" />
              baa_••••{apiKey.slice(-4)}
            </p>
          ) : null}
          <button
            type="button"
            onClick={() => dispatch(logout())}
            className="mt-3 flex w-full items-center justify-center gap-2 rounded-lg bg-white/10 px-3 py-1.5 text-sm font-medium text-slate-200 ring-1 ring-white/10 transition-colors ring-inset hover:bg-white/15 hover:text-white"
          >
            <Icon name="logout" className="h-4 w-4" />
            Disconnect
          </button>
        </div>
      </div>
    </div>
  )
}

/** Sidebar + top bar + content area for every page under /app. */
export default function AppLayout() {
  const dispatch = useDispatch()
  const location = useLocation()
  const health = useSelector((state) => state.health.state)
  const [menuOpen, setMenuOpen] = useState(false)

  useEffect(() => {
    dispatch(fetchHealth())
  }, [dispatch])

  // Escape closes the mobile menu, as people expect from any overlay.
  useEffect(() => {
    if (!menuOpen) return undefined
    const onKey = (event) => {
      if (event.key === 'Escape') setMenuOpen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [menuOpen])

  // Close the mobile menu after navigating. Done while rendering (not in an effect), the
  // way React recommends for resetting state when a value changes.
  const [lastPath, setLastPath] = useState(location.pathname)
  if (lastPath !== location.pathname) {
    setLastPath(location.pathname)
    setMenuOpen(false)
  }

  const crumbs = crumbsFor(location.pathname)

  return (
    <div className="bg-app-wash min-h-screen bg-slate-50">
      {/* Desktop sidebar */}
      <aside className="bg-ink fixed inset-y-0 left-0 z-20 hidden w-64 lg:block">
        <SidebarContent />
      </aside>

      {/* Mobile drawer */}
      {menuOpen ? (
        <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true">
          <button
            type="button"
            className="animate-backdrop-in absolute inset-0 bg-slate-900/30 backdrop-blur-sm"
            aria-label="Close menu"
            onClick={() => setMenuOpen(false)}
          />
          <aside className="animate-drawer-in bg-ink relative h-full w-72 max-w-[85%] shadow-xl">
            <button
              type="button"
              onClick={() => setMenuOpen(false)}
              className="absolute top-4 right-3 rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-white/10 hover:text-white"
              aria-label="Close menu"
            >
              <Icon name="close" />
            </button>
            <SidebarContent onNavigate={() => setMenuOpen(false)} />
          </aside>
        </div>
      ) : null}

      <div className="lg:pl-64">
        {/* Top bar: menu (mobile), breadcrumbs, API status, primary action */}
        <header className="sticky top-0 z-10 border-b border-slate-200/60 bg-white/70 backdrop-blur-xl">
          <div className="mx-auto flex h-16 max-w-7xl items-center gap-3 px-4 sm:px-6 lg:px-8">
            <button
              type="button"
              onClick={() => setMenuOpen(true)}
              className="-ml-1 rounded-lg p-2 text-slate-600 transition-colors hover:bg-slate-100 hover:text-slate-900 lg:hidden"
              aria-label="Open menu"
            >
              <Icon name="menu" />
            </button>
            <div className="lg:hidden">
              <Logo to={PATHS.app} compact />
            </div>
            <nav aria-label="Breadcrumb" className="hidden min-w-0 sm:block">
              <ol className="flex items-center gap-2 text-sm">
                <li className="text-slate-400">Workspace</li>
                {crumbs.map((crumb, index) => (
                  <li key={`${crumb.label}-${index}`} className="flex min-w-0 items-center gap-2">
                    <span className="text-slate-300">/</span>
                    {crumb.to && index < crumbs.length - 1 ? (
                      <Link to={crumb.to} className="truncate text-slate-500 transition-colors hover:text-indigo-700">
                        {crumb.label}
                      </Link>
                    ) : (
                      <span className="truncate font-medium text-slate-900">{crumb.label}</span>
                    )}
                  </li>
                ))}
              </ol>
            </nav>
            <div className="ml-auto flex items-center gap-3">
              <span
                className={`hidden items-center gap-2 rounded-full px-3 py-1 text-xs font-medium ring-1 ring-inset md:inline-flex ${HEALTH_STYLE[health].pill}`}
              >
                <HealthDot health={health} />
                {health === 'ok' ? 'Operational' : health === 'down' ? 'Degraded' : 'Checking'}
              </span>
              <ButtonLink to={PATHS.newRun} size="sm" aria-label="New audit run">
                <Icon name="plus" className="h-4 w-4" />
                <span className="hidden sm:inline">New run</span>
              </ButtonLink>
            </div>
          </div>
        </header>

        <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8 lg:px-8">
          {/* Keyed by URL so each page fades in when you navigate to it. */}
          <div key={location.pathname} className="animate-page-in">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
