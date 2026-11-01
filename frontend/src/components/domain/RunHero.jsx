import { PROVIDER_SHORT } from '../../utils/constants'
import { formatDateTime, formatNumber, humanize, shortId } from '../../utils/format'
import Icon from '../ui/Icon'
import ProgressRing from '../ui/ProgressRing'
import { RunStatusBadge } from './StatusBadges'

/** One setting of the run, as a small chip on the dark hero. */
function Chip({ label, value }) {
  return (
    <div className="min-w-0 rounded-xl bg-white/5 px-3 py-2 ring-1 ring-white/10 ring-inset">
      <p className="text-[10px] font-semibold tracking-wider text-indigo-200/60 uppercase">{label}</p>
      <p className="mt-0.5 text-sm font-medium break-words text-white">{value ?? '–'}</p>
    </div>
  )
}

/**
 * The top of the run page on a dark panel: ID, status, when it was created, the stored
 * configuration, and how much of the model-call budget has been used.
 */
export default function RunHero({ run, actions }) {
  const { config } = run
  return (
    <section className="bg-ink relative isolate mb-6 overflow-hidden rounded-3xl p-5 text-white shadow-float sm:p-8">
      <div className="bg-grid absolute inset-0 -z-10 opacity-[0.07] invert" aria-hidden />
      <div className="flex flex-col gap-8 lg:flex-row lg:items-center lg:justify-between">
        <div className="min-w-0 flex-1">
          <p className="inline-flex items-center gap-2 text-xs font-semibold tracking-wider text-indigo-200/70 uppercase">
            <Icon name="runs" className="h-3.5 w-3.5" />
            Audit run
          </p>
          <div className="mt-2 flex flex-wrap items-center gap-3">
            <h1 className="font-mono text-2xl font-bold tracking-tight sm:text-3xl">{shortId(run.id)}</h1>
            <RunStatusBadge status={run.status} />
          </div>
          <p className="mt-2 text-sm text-slate-400">Created {formatDateTime(run.created_at)}</p>

          <div className="mt-6 grid grid-cols-[repeat(auto-fill,minmax(7.25rem,1fr))] gap-2">
            <Chip label="Category" value={humanize(config.category)} />
            <Chip
              label="Prompts"
              value={config.prompt_ids?.length ? config.prompt_ids.join(', ') : 'All in category'}
            />
            <Chip label="Assistants" value={config.answer_providers?.map((p) => PROVIDER_SHORT[p] || humanize(p)).join(', ')} />
            <Chip label="Repeats" value={config.repeats} />
            <Chip label="Agent prompt" value={config.agent_version} />
          </div>
          {actions ? <div className="mt-6 flex flex-wrap gap-2">{actions}</div> : null}
        </div>

        <div className="flex items-center gap-5 rounded-2xl bg-white/5 p-5 ring-1 ring-white/10 ring-inset lg:flex-none">
          <ProgressRing
            value={run.model_calls}
            max={run.max_model_calls}
            className="text-white"
            label={`${run.model_calls} of ${run.max_model_calls} model calls used`}
          />
          <div>
            <p className="text-xs font-semibold tracking-wider text-indigo-200/70 uppercase">
              Model-call budget
            </p>
            <p className="mt-1 font-display text-2xl font-bold tabular-nums">
              {formatNumber(run.model_calls)}
              <span className="text-base font-medium text-slate-400"> / {formatNumber(run.max_model_calls)}</span>
            </p>
            <p className="mt-1 max-w-48 text-xs leading-5 text-slate-400">
              A hard cap. The run stops as “partial” when it is reached.
            </p>
          </div>
        </div>
      </div>
    </section>
  )
}
