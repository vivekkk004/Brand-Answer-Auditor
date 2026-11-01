import { useEffect } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { useLocation, useParams } from 'react-router-dom'
import InclusionTable from '../components/domain/InclusionTable'
import LabelShareBar from '../components/domain/LabelShareBar'
import RunHero from '../components/domain/RunHero'
import Alert from '../components/ui/Alert'
import { Button } from '../components/ui/Button'
import Card from '../components/ui/Card'
import ErrorBanner from '../components/ui/ErrorBanner'
import Icon from '../components/ui/Icon'
import LoadingState from '../components/ui/LoadingState'
import PageHeader from '../components/ui/PageHeader'
import Spinner from '../components/ui/Spinner'
import StatCard from '../components/ui/StatCard'
import { fetchRun, selectRunById } from '../features/runs/runsSlice'
import { PATHS } from '../routes/paths'
import { ACTIVE_RUN_STATUSES } from '../utils/constants'
import { formatDateTime, formatNumber, formatPercent, formatUsd, humanize } from '../utils/format'

const POLL_MS = 3000

function Timeline({ run }) {
  const steps = [
    { label: 'Queued', at: run.created_at, done: true },
    { label: 'Started', at: run.started_at, done: Boolean(run.started_at) },
    { label: humanize(run.finished_at ? run.status : 'finished'), at: run.finished_at, done: Boolean(run.finished_at) },
  ]
  const active = ACTIVE_RUN_STATUSES.includes(run.status)
  return (
    <ol>
      {steps.map((step, index) => {
        // The first unfinished step of an active run is the one happening now.
        const current = active && !step.done && steps[index - 1]?.done
        const next = steps[index + 1]
        return (
          <li key={step.label} className="relative flex items-start gap-3 pb-5 last:pb-0">
            {next ? (
              <span
                className={`absolute top-6 bottom-0 left-[9px] w-0.5 rounded-full ${
                  next.done ? 'bg-indigo-600' : 'bg-slate-200'
                }`}
                aria-hidden
              />
            ) : null}
            <span
              className={`relative mt-0.5 flex h-5 w-5 flex-none items-center justify-center rounded-full transition-colors ${
                step.done
                  ? 'bg-indigo-600 text-white'
                  : current
                    ? 'border-2 border-indigo-400 bg-white'
                    : 'border-2 border-slate-200 bg-white'
              }`}
            >
              {step.done ? <Icon name="check" className="h-3 w-3" /> : null}
              {current ? <span className="h-2 w-2 animate-pulse rounded-full bg-indigo-500" /> : null}
            </span>
            <div>
              <p className={`text-sm font-medium ${step.done ? 'text-slate-900' : 'text-slate-400'}`}>
                {step.label}
              </p>
              <p className="text-xs text-slate-500">
                {step.done ? formatDateTime(step.at) : current ? 'In progress' : 'Waiting'}
              </p>
            </div>
          </li>
        )
      })}
    </ol>
  )
}

function TokensTable({ tokens }) {
  const rows = ['generation', 'verification', 'total']
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm tabular-nums">
        <thead>
          <tr className="border-b border-slate-200 text-left text-[11px] tracking-wider text-slate-500 uppercase">
            <th className="pb-2.5 font-semibold">Phase</th>
            <th className="pb-2.5 pl-4 text-right font-semibold">Input</th>
            <th className="pb-2.5 pl-4 text-right font-semibold">Output</th>
            <th className="pb-2.5 pl-4 text-right font-semibold">Thinking</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {rows.map((phase) => (
            <tr
              key={phase}
              className={phase === 'total' ? 'border-t border-slate-200 font-semibold text-slate-900' : 'text-slate-700'}
            >
              <td className="py-2.5">{humanize(phase)}</td>
              <td className="py-2.5 pl-4 text-right">{formatNumber(tokens?.[phase]?.input)}</td>
              <td className="py-2.5 pl-4 text-right">{formatNumber(tokens?.[phase]?.output)}</td>
              <td className="py-2.5 pl-4 text-right">{formatNumber(tokens?.[phase]?.thinking)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function Metrics({ metrics, progress }) {
  const answers = metrics.answers || {}
  const errors = Object.entries(metrics.errors_by_type || {})
  const failed = (answers.generation_failed || 0) + (answers.verification_failed || 0)
  // Shares for the bars under the numbers, computed from the run's own counts.
  const shareOf = (count) => (answers.total ? count / answers.total : null)
  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Answers" value={formatNumber(answers.total)} icon="runs" hint="Collected from the assistants" />
        <StatCard
          label="Verified"
          value={formatNumber(answers.verified)}
          icon="check"
          tone="green"
          progress={shareOf(answers.verified || 0)}
          hint={`${formatPercent(shareOf(answers.verified || 0))} of answers`}
        />
        <StatCard
          label="Failed"
          value={formatNumber(failed)}
          icon="alert"
          tone="red"
          progress={shareOf(failed)}
          hint="Generation + verification"
        />
        <StatCard
          label="Estimated cost"
          value={formatUsd(metrics.cost_usd)}
          icon="bolt"
          tone="amber"
          hint="From reported tokens"
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-3 lg:items-start">
        <Card
          className="lg:col-span-2"
          title="Brand inclusion"
          description="How often each brand was named, with a 95% Wilson confidence interval."
          icon={<Icon name="chart" className="h-5 w-5" />}
          bodyClassName=""
        >
          <InclusionTable inclusion={metrics.inclusion} />
        </Card>
        <div className="min-w-0 space-y-6">
          <Card
            title="Claim labels"
            description={`${formatNumber(metrics.claims?.total ?? 0)} verified claims`}
            icon={<Icon name="verify" className="h-5 w-5" />}
          >
            <LabelShareBar labels={metrics.claims?.labels || {}} total={metrics.claims?.total} />
          </Card>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2 lg:items-start">
        {progress}
        <Card
          title="Failures by type"
          description="Each failure is typed, so it can be fixed at the source."
          icon={<Icon name="alert" className="h-5 w-5" />}
        >
          {errors.length ? (
            <ul className="divide-y divide-slate-100">
              {errors.map(([type, count]) => (
                <li key={type} className="flex items-center justify-between py-2.5 text-sm first:pt-0 last:pb-0">
                  <span className="font-medium text-slate-700">{humanize(type)}</span>
                  <span className="rounded-full bg-rose-50 px-2.5 py-0.5 text-xs font-semibold text-rose-700 tabular-nums ring-1 ring-rose-200 ring-inset">
                    {formatNumber(count)}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="flex items-center gap-2 text-sm text-slate-500">
              <Icon name="check" className="h-4 w-4 text-emerald-500" />
              No failures.
            </p>
          )}
        </Card>
      </div>

      <div>
        <Card
          title="Tokens"
          description="As reported by the providers, never estimated."
          icon={<Icon name="code" className="h-5 w-5" />}
        >
          <TokensTable tokens={metrics.tokens} />
        </Card>
      </div>
    </div>
  )
}

export default function RunDetailPage() {
  const { runId } = useParams()
  const location = useLocation()
  const dispatch = useDispatch()
  const run = useSelector(selectRunById(runId))
  const { status, error } = useSelector((state) => state.runs.detail)

  // Keep polling while the run can still change; stop once it is final or failed to load.
  const active = run ? ACTIVE_RUN_STATUSES.includes(run.status) : !error

  useEffect(() => {
    dispatch(fetchRun(runId))
  }, [dispatch, runId])

  useEffect(() => {
    if (!active) return undefined
    const timer = setInterval(() => dispatch(fetchRun(runId)), POLL_MS)
    return () => clearInterval(timer)
  }, [active, dispatch, runId])

  if (!run) {
    return (
      <>
        <PageHeader title="Audit run" back={{ to: PATHS.runs, label: 'Audit runs' }} />
        {status === 'failed' ? (
          <ErrorBanner error={error} title="Could not load this run" onRetry={() => dispatch(fetchRun(runId))} />
        ) : (
          <LoadingState label="Loading run…" />
        )}
      </>
    )
  }

  const progress = (
    <Card title="Progress" icon={<Icon name="runs" className="h-5 w-5" />}>
      <Timeline run={run} />
    </Card>
  )

  return (
    <>
      <PageHeader back={{ to: PATHS.runs, label: 'Audit runs' }} />
      <RunHero
        run={run}
        actions={
          <Button variant="glass" size="sm" onClick={() => dispatch(fetchRun(runId))} loading={status === 'loading'}>
            <Icon name="refresh" className="h-4 w-4" />
            Refresh
          </Button>
        }
      />

      {location.state?.replayed ? (
        <div className="mb-6">
          <Alert tone="info">
            This request was already made, so the existing run is shown — no second run was started.
          </Alert>
        </div>
      ) : null}

      {run.failure_reason ? (
        <div className="mb-6">
          <ErrorBanner error={{ message: run.failure_reason }} title="The run failed" />
        </div>
      ) : null}

      {run.metrics ? (
        <Metrics metrics={run.metrics} progress={progress} />
      ) : (
        <div className="grid gap-6 lg:grid-cols-3 lg:items-start">
          {progress}
          <Card className="lg:col-span-2">
            <div className="flex items-start gap-4">
              <div className="flex h-10 w-10 flex-none items-center justify-center rounded-full bg-indigo-50 ring-1 ring-indigo-100">
                <Spinner className="h-5 w-5 text-indigo-600" />
              </div>
              <div className="text-sm leading-6 text-slate-600">
                <p className="font-medium text-slate-900">Metrics appear when the run finishes.</p>
                <p className="mt-1">
                  This page refreshes every {POLL_MS / 1000} seconds while the run is queued or
                  running. Runs are processed by a separate worker (
                  <code className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-700">auditor worker</code>
                  ); if it stays queued, check that a worker is running and configured.
                </p>
              </div>
            </div>
          </Card>
        </div>
      )}
    </>
  )
}
