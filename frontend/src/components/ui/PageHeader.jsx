import { Link } from 'react-router-dom'
import Icon from './Icon'

/**
 * Top of every app page: an optional back link, then (if given) a small eyebrow label,
 * the title, a description and actions on the right. A page with its own hero passes
 * only `back`.
 */
export default function PageHeader({ title, description, actions, back, eyebrow }) {
  return (
    <div className={title ? 'mb-6 sm:mb-8' : 'mb-4'}>
      {back ? (
        <Link
          to={back.to}
          className={`group inline-flex items-center gap-1.5 rounded-md text-sm font-medium text-slate-500 transition-colors hover:text-indigo-700 ${title ? 'mb-4' : ''}`}
        >
          <Icon name="arrowLeft" className="h-4 w-4 transition-transform group-hover:-translate-x-0.5" />
          {back.label}
        </Link>
      ) : null}
      {title ? (
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div className="min-w-0">
            {eyebrow ? (
              <p className="mb-2 inline-flex items-center gap-2 text-xs font-semibold tracking-wider text-indigo-600 uppercase">
                <span className="h-1.5 w-1.5 rounded-full bg-gradient-to-r from-indigo-500 to-violet-500" />
                {eyebrow}
              </p>
            ) : null}
            <h1 className="text-2xl font-extrabold tracking-tight text-slate-900 sm:text-[32px] sm:leading-10">
              {title}
            </h1>
            {description ? (
              <p className="mt-2 max-w-2xl text-[15px] leading-6 text-slate-500">{description}</p>
            ) : null}
          </div>
          {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
        </div>
      ) : null}
    </div>
  )
}
