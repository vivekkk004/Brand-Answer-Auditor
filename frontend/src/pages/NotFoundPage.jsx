import { ButtonLink } from '../components/ui/Button'
import Icon from '../components/ui/Icon'
import { PATHS } from '../routes/paths'

export default function NotFoundPage() {
  return (
    <div className="animate-page-in mx-auto max-w-xl px-4 py-20 text-center sm:py-28">
      <div className="relative mx-auto mb-6 w-fit">
        <div className="absolute inset-0 scale-150 rounded-full bg-indigo-100/70 blur-xl" />
        <div className="relative flex h-14 w-14 items-center justify-center rounded-2xl bg-white text-indigo-600 shadow-sm ring-1 ring-slate-200">
          <Icon name="compass" className="h-6 w-6" />
        </div>
      </div>
      <p className="text-sm font-semibold text-indigo-600">404</p>
      <h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">Page not found</h1>
      <p className="mt-3 text-slate-600">The page you are looking for does not exist.</p>
      <div className="mt-8 flex flex-wrap justify-center gap-3">
        <ButtonLink to={PATHS.home}>
          <Icon name="arrowLeft" className="h-4 w-4" />
          Back to home
        </ButtonLink>
        <ButtonLink to={PATHS.app} variant="secondary">
          Open dashboard
        </ButtonLink>
      </div>
    </div>
  )
}
