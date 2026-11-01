import { useSelector } from 'react-redux'
import { Link, Outlet } from 'react-router-dom'
import { selectIsAuthenticated } from '../../features/auth/authSlice'
import { PATHS } from '../../routes/paths'
import { ButtonLink } from '../ui/Button'
import Icon from '../ui/Icon'
import Logo from '../ui/Logo'

const NAV_LINKS = [
  { href: '/#features', label: 'Features' },
  { href: '/#how-it-works', label: 'How it works' },
  { href: '/#api', label: 'API' },
  { href: '/#reliability', label: 'Reliability' },
]

const FOOTER_COLUMNS = [
  {
    title: 'Product',
    links: [
      { href: '/#features', label: 'Features' },
      { href: '/#how-it-works', label: 'How it works' },
      { href: '/#reliability', label: 'Reliability' },
    ],
  },
  {
    title: 'Developers',
    links: [
      { href: '/#api', label: 'REST API' },
      { href: PATHS.connect, label: 'Connect an API key', internal: true },
    ],
  },
]

/** Top navigation and footer for the landing page, connect page and 404. */
export default function PublicLayout() {
  const isAuthenticated = useSelector(selectIsAuthenticated)

  return (
    <div className="flex min-h-screen flex-col bg-white">
      <header className="sticky top-0 z-30 border-b border-slate-200/70 bg-white/75 backdrop-blur-lg">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-6 px-4 sm:px-6 lg:px-8">
          <Logo />
          <nav className="hidden items-center gap-1 md:flex" aria-label="Main">
            {NAV_LINKS.map((link) => (
              <a
                key={link.href}
                href={link.href}
                className="rounded-lg px-3 py-2 text-sm font-medium text-slate-600 transition-colors hover:bg-slate-100 hover:text-slate-900"
              >
                {link.label}
              </a>
            ))}
          </nav>
          <div className="flex items-center gap-2">
            {isAuthenticated ? null : (
              <Link
                to={PATHS.connect}
                className="hidden rounded-lg px-3 py-2 text-sm font-semibold text-slate-700 hover:text-slate-900 sm:block"
              >
                Sign in
              </Link>
            )}
            <ButtonLink to={isAuthenticated ? PATHS.app : PATHS.connect} size="sm">
              {isAuthenticated ? 'Open dashboard' : 'Connect API key'}
              <Icon name="arrowRight" className="h-3.5 w-3.5" />
            </ButtonLink>
          </div>
        </div>
      </header>

      <main className="flex-1">
        <Outlet />
      </main>

      <footer className="border-t border-slate-200 bg-slate-50/80">
        <div className="mx-auto grid max-w-7xl gap-10 px-4 py-14 sm:px-6 md:grid-cols-4 lg:px-8">
          <div className="md:col-span-2">
            <Logo />
            <p className="mt-4 max-w-sm text-sm leading-6 text-slate-500">
              Measures how often AI assistants recommend a brand, and checks what they claim
              against the brand’s own fact catalogue — with a person in the loop.
            </p>
          </div>
          {FOOTER_COLUMNS.map((column) => (
            <div key={column.title}>
              <h3 className="text-sm font-semibold text-slate-900">{column.title}</h3>
              <ul className="mt-4 space-y-3">
                {column.links.map((link) => (
                  <li key={link.label}>
                    {link.internal ? (
                      <Link to={link.href} className="text-sm text-slate-500 hover:text-indigo-700">
                        {link.label}
                      </Link>
                    ) : (
                      <a href={link.href} className="text-sm text-slate-500 hover:text-indigo-700">
                        {link.label}
                      </a>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <div className="border-t border-slate-200">
          <div className="mx-auto flex max-w-7xl flex-col gap-2 px-4 py-6 text-xs text-slate-500 sm:flex-row sm:justify-between sm:px-6 lg:px-8">
            <span>Brand Answer Auditor — a portfolio project.</span>
            <span>All brands and facts in the demo data are fictional.</span>
          </div>
        </div>
      </footer>
    </div>
  )
}
