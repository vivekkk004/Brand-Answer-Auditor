import { Link } from 'react-router-dom'
import { runPath } from '../../routes/paths'
import { PROVIDER_SHORT } from '../../utils/constants'
import { formatNumber, humanize, shortId } from '../../utils/format'
import Icon from '../ui/Icon'

// A colour dot per assistant, so the two providers are easy to tell apart in a list.
const PROVIDER_DOT = { gemini: 'bg-sky-500', openai: 'bg-emerald-500' }

/** The run's short ID as a link, with a small icon tile and its category underneath. */
export function RunIdCell({ run }) {
  return (
    <div className="flex items-center gap-3">
      <div className="flex h-9 w-9 flex-none items-center justify-center rounded-lg bg-gradient-to-br from-indigo-50 to-violet-50 text-indigo-600 ring-1 ring-indigo-100">
        <Icon name="runs" className="h-4 w-4" />
      </div>
      <div className="min-w-0">
        <Link
          to={runPath(run.id)}
          className="font-mono text-[13px] font-semibold text-slate-900 hover:text-indigo-700 hover:underline"
          onClick={(event) => event.stopPropagation()}
        >
          {shortId(run.id)}
        </Link>
        <p className="text-xs text-slate-500">{humanize(run.config.category)}</p>
      </div>
    </div>
  )
}

/** The assistants a run asks, as small chips. */
export function ProviderChips({ providers }) {
  return (
    <div className="flex gap-1.5 whitespace-nowrap">
      {(providers || []).map((provider) => (
        <span
          key={provider}
          className="inline-flex items-center gap-1.5 rounded-md bg-slate-50 px-2 py-0.5 text-xs font-medium text-slate-700 ring-1 ring-slate-200 ring-inset"
        >
          <span className={`h-1.5 w-1.5 rounded-full ${PROVIDER_DOT[provider] || 'bg-slate-400'}`} />
          {PROVIDER_SHORT[provider] || humanize(provider)}
        </span>
      ))}
    </div>
  )
}

/** Model calls used against the run's budget: the numbers plus a thin bar. */
export function BudgetBar({ used, max }) {
  const share = max ? Math.min(1, used / max) : 0
  return (
    <div className="w-32">
      <p className="text-xs font-medium text-slate-700 tabular-nums">
        {formatNumber(used)} / {formatNumber(max)}
      </p>
      <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-slate-100" aria-hidden>
        <div
          className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-violet-500 transition-[width] duration-700"
          style={{ width: `${share * 100}%` }}
        />
      </div>
    </div>
  )
}
