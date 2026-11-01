import { Link } from 'react-router-dom'
import Icon from './Icon'

/** Title row at the top of every app page, with an optional back link and actions. */
export default function PageHeader({ title, description, actions, back }) {
  return (
    <div className="mb-6 sm:mb-8">
      {back ? (
        <Link
          to={back.to}
          className="group mb-4 inline-flex items-center gap-1.5 rounded-md text-sm font-medium text-slate-500 transition-colors hover:text-indigo-700"
        >
          <Icon name="arrowLeft" className="h-4 w-4 transition-transform group-hover:-translate-x-0.5" />
          {back.label}
        </Link>
      ) : null}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 sm:text-[28px]">{title}</h1>
          {description ? (
            <p className="mt-1.5 max-w-2xl text-[15px] leading-6 text-slate-500">{description}</p>
          ) : null}
        </div>
        {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
      </div>
    </div>
  )
}
