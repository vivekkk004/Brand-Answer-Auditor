import { useEffect, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { logout } from '../../features/auth/authSlice'
import { fetchHealth } from '../../features/health/healthSlice'
import { PATHS } from '../../routes/paths'
import Icon from '../ui/Icon'
import Logo from '../ui/Logo'

const NAV_ITEMS = [
  { to: PATHS.app, label: 'Overview', icon: 'home', end: true },
  { to: PATHS.runs, label: 'Audit runs', icon: 'runs' },
  { to: PATHS.verify, label: 'Verify answer', icon: 'verify' },
  { to: PATHS.review, label: 'Review queue', icon: 'review' },
]

const HEALTH_STYLE = {
  ok: { dot: 'bg-emerald-500', text: 'API connected' },
  down: { dot: 'bg-rose-500', text: 'API unavailable' },
  unknown: { dot: 'bg-slate-300', text: 'Checking API…' },
}

function SidebarContent({ onNavigate }) {
  const dispatch = useDispatch()
  const health = useSelector((state) => state.health.state)
  const style = HEALTH_STYLE[health]

  return (
    <div className="flex h-full flex-col">
      <div className="flex h-16 items-center border-b border-slate-200 px-5">
        <Logo to={PATHS.app} />
      </div>
      <nav className="flex-1 space-y-1 px-3 py-4" aria-label="App">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            onClick={onNavigate}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-indigo-50 text-indigo-700'
                  : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
              }`
            }
          >
            <Icon name={item.icon} />
            {item.label}
          </NavLink>
        ))}
      </nav>
      <div className="space-y-3 border-t border-slate-200 p-4">
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <span className={`h-2 w-2 rounded-full ${style.dot}`} />
          {style.text}
        </div>
        <button
          type="button"
          onClick={() => dispatch(logout())}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900"
        >
          <Icon name="logout" />
          Disconnect
        </button>
      </div>
    </div>
  )
}

/** Sidebar + content area for every page under /app. */
export default function AppLayout() {
  const dispatch = useDispatch()
  const location = useLocation()
  const [menuOpen, setMenuOpen] = useState(false)

  useEffect(() => {
    dispatch(fetchHealth())
  }, [dispatch])

  // Close the mobile menu after navigating. Done while rendering (not in an effect), the
  // way React recommends for resetting state when a value changes.
  const [lastPath, setLastPath] = useState(location.pathname)
  if (lastPath !== location.pathname) {
    setLastPath(location.pathname)
    setMenuOpen(false)
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-64 border-r border-slate-200 bg-white lg:block">
        <SidebarContent />
      </aside>

      {/* Mobile top bar and drawer */}
      <div className="sticky top-0 z-20 flex h-14 items-center justify-between border-b border-slate-200 bg-white px-4 lg:hidden">
        <Logo to={PATHS.app} />
        <button
          type="button"
          onClick={() => setMenuOpen(true)}
          className="rounded-lg p-2 text-slate-600 hover:bg-slate-100"
          aria-label="Open menu"
        >
          <Icon name="menu" />
        </button>
      </div>
      {menuOpen ? (
        <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true">
          <button
            type="button"
            className="absolute inset-0 bg-slate-900/30"
            aria-label="Close menu"
            onClick={() => setMenuOpen(false)}
          />
          <aside className="relative h-full w-72 max-w-[85%] bg-white shadow-xl">
            <button
              type="button"
              onClick={() => setMenuOpen(false)}
              className="absolute top-4 right-3 rounded-lg p-1.5 text-slate-500 hover:bg-slate-100"
              aria-label="Close menu"
            >
              <Icon name="close" />
            </button>
            <SidebarContent onNavigate={() => setMenuOpen(false)} />
          </aside>
        </div>
      ) : null}

      <main className="lg:pl-64">
        <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
