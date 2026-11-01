import { useSelector } from 'react-redux'
import { Link, Outlet } from 'react-router-dom'
import { selectIsAuthenticated } from '../../features/auth/authSlice'
import { PATHS } from '../../routes/paths'
import { ButtonLink } from '../ui/Button'
import Logo from '../ui/Logo'

const NAV_LINKS = [
  { href: '/#features', label: 'Features' },
  { href: '/#how-it-works', label: 'How it works' },
  { href: '/#reliability', label: 'Reliability' },
]

/** Top navigation and footer for the landing page, connect page and 404. */
export default function PublicLayout() {
  const isAuthenticated = useSelector(selectIsAuthenticated)

  return (
    <div className="flex min-h-screen flex-col bg-white">
      <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/90 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-6 px-4 sm:px-6 lg:px-8">
          <Logo />
          <nav className="hidden items-center gap-8 md:flex" aria-label="Main">
            {NAV_LINKS.map((link) => (
              <a
                key={link.href}
                href={link.href}
                className="text-sm font-medium text-slate-600 hover:text-slate-900"
              >
                {link.label}
              </a>
            ))}
          </nav>
          <ButtonLink to={isAuthenticated ? PATHS.app : PATHS.connect} size="sm">
            {isAuthenticated ? 'Open dashboard' : 'Connect API key'}
          </ButtonLink>
        </div>
      </header>

      <main className="flex-1">
        <Outlet />
      </main>

      <footer className="border-t border-slate-200 bg-slate-50">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-8 text-sm text-slate-500 sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <Logo compact />
            <span>Brand Answer Auditor — a portfolio project.</span>
          </div>
          <div className="flex flex-wrap gap-x-6 gap-y-2">
            <span>All brands and facts in the demo data are fictional.</span>
            <Link to={PATHS.connect} className="font-medium text-slate-600 hover:text-slate-900">
              Sign in
            </Link>
          </div>
        </div>
      </footer>
    </div>
  )
}
