import { ButtonLink } from '../components/ui/Button'
import { PATHS } from '../routes/paths'

export default function NotFoundPage() {
  return (
    <div className="mx-auto max-w-xl px-4 py-24 text-center">
      <p className="text-sm font-semibold text-indigo-600">404</p>
      <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-900">Page not found</h1>
      <p className="mt-3 text-slate-600">The page you are looking for does not exist.</p>
      <div className="mt-8">
        <ButtonLink to={PATHS.home}>Back to home</ButtonLink>
      </div>
    </div>
  )
}
