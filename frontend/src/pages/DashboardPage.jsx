import { useEffect } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { Link, useNavigate } from 'react-router-dom'
import { BudgetBar, ProviderChips, RunIdCell } from '../components/domain/RunCells'
import { RunStatusBadge } from '../components/domain/StatusBadges'
import { ButtonLink } from '../components/ui/Button'
import Card from '../components/ui/Card'
import EmptyState from '../components/ui/EmptyState'
import ErrorBanner from '../components/ui/ErrorBanner'
import Icon from '../components/ui/Icon'
import LoadingState from '../components/ui/LoadingState'
import ProgressRing from '../components/ui/ProgressRing'
import StatCard from '../components/ui/StatCard'
import Table from '../components/ui/Table'
import { fetchOpenReviewCount, OPEN_COUNT_LIMIT } from '../features/review/reviewSlice'
import { fetchRecentRuns } from '../features/runs/runsSlice'
import { PATHS, runPath } from '../routes/paths'
import { ACTIVE_RUN_STATUSES } from '../utils/constants'
import { formatDateTime, formatNumber, shortId } from '../utils/format'

const QUICK_ACTIONS = [
  { to: PATHS.newRun, icon: 'plus', title: 'Start an audit run', text: 'Ask assistants your category prompts and verify every answer.' },
  { to: PATHS.verify, icon: 'verify', title: 'Verify one answer', text: 'Paste any AI answer and check its claims right now.' },
  { to: PATHS.review, icon: 'review', title: 'Work the review queue', text: 'Confirm or dismiss contradicted claims.' },
]

/** The newest run, shown inside the dark hero: status, budget ring and a link. */
function LatestRunPanel({ run }) {
  if (!run) {
    return (
      <div className="rounded-2xl bg-white/5 p-5 text-sm text-slate-300 ring-1 ring-white/10 ring-inset">
        No runs yet. Queue one to see it here.
      </div>
    )
  }
  return (
    <Link
      to={runPath(run.id)}
      className="group flex items-center gap-5 rounded-2xl bg-white/5 p-5 ring-1 ring-white/10 transition-colors ring-inset hover:bg-white/10"
    >
      <ProgressRing
        value={run.model_calls}
        max={run.max_model_calls}
        size={88}
        stroke={8}
        className="text-white"
        label={`${run.model_calls} of ${run.max_model_calls} model calls used`}
      />
      <div className="min-w-0">
        <p className="text-xs font-semibold tracking-wider text-indigo-200/70 uppercase">Latest run</p>
        <div className="mt-1.5 flex flex-wrap items-center gap-2">
          <span className="font-mono text-lg font-bold text-white">{shortId(run.id)}</span>
          <RunStatusBadge status={run.status} />
        </div>
        <p className="mt-1 text-xs text-slate-400">
          {formatNumber(run.model_calls)} / {formatNumber(run.max_model_calls)} model calls ·{' '}
          {formatDateTime(run.created_at)}
        </p>
      </div>
      <Icon
        name="arrowRight"
        className="ml-auto hidden h-5 w-5 flex-none text-slate-500 transition-all group-hover:translate-x-0.5 group-hover:text-white sm:block"
      />
    </Link>
  )
}

export default function DashboardPage() {
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const health = useSelector((state) => state.health.state)
  const recent = useSelector((state) => state.runs.recent)
  const openCount = useSelector((state) => state.review.openCount)

  useEffect(() => {
    dispatch(fetchRecentRuns())
    dispatch(fetchOpenReviewCount())
  }, [dispatch])

  const latest = recent.items[0]
  const openValue =
    openCount.value === null
      ? '–'
      : openCount.value >= OPEN_COUNT_LIMIT
        ? `${OPEN_COUNT_LIMIT}+`
        : openCount.value
  // Counted only among the runs this page loaded (the newest few), and labelled that way.
  const activeCount = recent.items.filter((run) => ACTIVE_RUN_STATUSES.includes(run.status)).length

  const columns = [
    { key: 'id', header: 'Run', render: (run) => <RunIdCell run={run} /> },
    { key: 'status', header: 'Status', render: (run) => <RunStatusBadge status={run.status} /> },
    {
      key: 'providers',
      header: 'Assistants',
      // The dashboard card is narrower than the runs page, so this column waits for room.
      className: 'hidden 2xl:table-cell',
      render: (run) => <ProviderChips providers={run.config.answer_providers} />,
    },
    {
      key: 'calls',
      header: 'Budget',
      className: 'hidden sm:table-cell',
      render: (run) => <BudgetBar used={run.model_calls} max={run.max_model_calls} />,
    },
    {
      key: 'created',
      header: 'Created',
      className: 'whitespace-nowrap text-slate-500',
      render: (run) => formatDateTime(run.created_at),
    },
  ]

  return (
    <>
      {/* Welcome hero */}
      <section className="bg-ink relative isolate mb-6 overflow-hidden rounded-3xl px-5 py-7 text-white shadow-float sm:mb-8 sm:px-8 sm:py-9">
        <div className="bg-grid absolute inset-0 -z-10 opacity-[0.07] invert" aria-hidden />
        <div className="animate-aurora absolute -top-24 right-1/4 -z-10 h-64 w-64 rounded-full bg-violet-500/25 blur-3xl" aria-hidden />
        <div className="grid items-center gap-8 lg:grid-cols-[1fr_auto]">
          <div className="max-w-xl">
            <p className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-xs font-semibold text-indigo-100 ring-1 ring-white/15 ring-inset">
              <Icon name="sparkles" className="h-3.5 w-3.5 text-indigo-300" />
              Overview
            </p>
            <h1 className="mt-4 text-3xl font-extrabold tracking-tight sm:text-4xl">
              Your AI answer audits{' '}
              <span className="bg-gradient-to-r from-indigo-300 via-violet-300 to-sky-300 bg-clip-text text-transparent">
                at a glance
              </span>
            </h1>
            <p className="mt-3 text-[15px] leading-7 text-slate-300">
              Queue runs, follow their progress and clear the review queue.
            </p>
            <div className="mt-6 flex w-full flex-wrap gap-3 sm:w-auto">
              <ButtonLink to={PATHS.newRun} variant="white" className="flex-1 sm:flex-none">
                <Icon name="plus" className="h-4 w-4" />
                New audit run
              </ButtonLink>
              <ButtonLink to={PATHS.verify} variant="glass" className="flex-1 sm:flex-none">
                <Icon name="verify" className="h-4 w-4" />
                Verify an answer
              </ButtonLink>
            </div>
          </div>
          <div className="lg:w-96">
            <LatestRunPanel run={latest} />
          </div>
        </div>
      </section>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <StatCard
          label="API status"
          value={health === 'ok' ? 'Healthy' : health === 'down' ? 'Unavailable' : 'Checking…'}
          hint="API and database reachable"
          icon="shield"
          tone={health === 'ok' ? 'green' : health === 'down' ? 'red' : 'slate'}
        />
        <StatCard
          label="Open review items"
          value={openValue}
          hint="Contradicted claims waiting for a person"
          icon="review"
          tone={openCount.value ? 'amber' : 'indigo'}
        />
        <StatCard
          label="Runs in progress"
          value={recent.items.length ? activeCount : '–'}
          hint={`Queued or running, among the ${recent.items.length || 'newest'} newest runs`}
          icon="bolt"
          tone="indigo"
        />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-3 lg:items-start">
        <Card
          className="lg:col-span-2"
          title="Recent runs"
          description="The five newest audit runs."
          icon={<Icon name="runs" className="h-5 w-5" />}
          bodyClassName=""
          actions={
            <Link
              to={PATHS.runs}
              className="group inline-flex items-center gap-1 text-sm font-semibold text-indigo-700 transition-colors hover:text-indigo-500"
            >
              View all
              <Icon name="arrowRight" className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
            </Link>
          }
        >
          {(recent.status === 'idle' || recent.status === 'loading') && !recent.items.length ? (
            <LoadingState label="Loading runs…" />
          ) : recent.status === 'failed' ? (
            <div className="p-5">
              <ErrorBanner error={recent.error} onRetry={() => dispatch(fetchRecentRuns())} />
            </div>
          ) : (
            <Table
              columns={columns}
              rows={recent.items}
              onRowClick={(run) => navigate(runPath(run.id))}
              empty={
                <EmptyState
                  title="No audit runs yet"
                  description="Queue your first run to start measuring brand inclusion."
                  action={<ButtonLink to={PATHS.newRun}>New audit run</ButtonLink>}
                />
              }
            />
          )}
        </Card>

        <Card title="Quick actions" icon={<Icon name="bolt" className="h-5 w-5" />}>
          <ul className="-mx-2 space-y-1">
            {QUICK_ACTIONS.map((action) => (
              <li key={action.to}>
                <Link
                  to={action.to}
                  className="group flex items-center gap-3 rounded-xl p-3 transition-colors duration-150 hover:bg-indigo-50/60"
                >
                  <div className="flex h-10 w-10 flex-none items-center justify-center rounded-xl bg-slate-100 text-slate-600 transition-all group-hover:bg-gradient-to-br group-hover:from-indigo-500 group-hover:to-violet-600 group-hover:text-white group-hover:shadow-md group-hover:shadow-indigo-500/30">
                    <Icon name={action.icon} className="h-5 w-5" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-semibold text-slate-900 transition-colors group-hover:text-indigo-700">
                      {action.title}
                    </p>
                    <p className="mt-0.5 text-xs leading-5 text-slate-500">{action.text}</p>
                  </div>
                  <Icon
                    name="arrowRight"
                    className="h-4 w-4 flex-none text-slate-300 transition-all group-hover:translate-x-0.5 group-hover:text-indigo-500"
                  />
                </Link>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </>
  )
}
