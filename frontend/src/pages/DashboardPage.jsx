import { useEffect } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { Link, useNavigate } from 'react-router-dom'
import { RunStatusBadge } from '../components/domain/StatusBadges'
import { ButtonLink } from '../components/ui/Button'
import Card from '../components/ui/Card'
import EmptyState from '../components/ui/EmptyState'
import ErrorBanner from '../components/ui/ErrorBanner'
import Icon from '../components/ui/Icon'
import LoadingState from '../components/ui/LoadingState'
import StatCard from '../components/ui/StatCard'
import Table from '../components/ui/Table'
import { fetchOpenReviewCount, OPEN_COUNT_LIMIT } from '../features/review/reviewSlice'
import { fetchRecentRuns } from '../features/runs/runsSlice'
import { PATHS, runPath } from '../routes/paths'
import { formatDateTime, humanize, shortId } from '../utils/format'

const QUICK_ACTIONS = [
  { to: PATHS.newRun, icon: 'plus', title: 'Start an audit run', text: 'Ask assistants your category prompts and verify every answer.' },
  { to: PATHS.verify, icon: 'verify', title: 'Verify one answer', text: 'Paste any AI answer and check its claims right now.' },
  { to: PATHS.review, icon: 'review', title: 'Work the review queue', text: 'Confirm or dismiss contradicted claims.' },
]

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

  const columns = [
    {
      key: 'id',
      header: 'Run',
      render: (run) => (
        <Link
          to={runPath(run.id)}
          className="font-mono text-xs font-medium text-indigo-700 hover:underline"
          onClick={(event) => event.stopPropagation()}
        >
          {shortId(run.id)}
        </Link>
      ),
    },
    { key: 'status', header: 'Status', render: (run) => <RunStatusBadge status={run.status} /> },
    { key: 'category', header: 'Category', render: (run) => humanize(run.config.category) },
    {
      key: 'created',
      header: 'Created',
      className: 'whitespace-nowrap',
      render: (run) => formatDateTime(run.created_at),
    },
  ]

  return (
    <>
      {/* Welcome banner */}
      <section className="relative isolate mb-6 overflow-hidden rounded-3xl bg-gradient-to-br from-indigo-600 via-indigo-600 to-violet-600 px-5 py-7 text-white shadow-float sm:mb-8 sm:px-10 sm:py-9">
        <div className="bg-grid absolute inset-0 -z-10 opacity-20 invert" />
        <div className="animate-aurora absolute -top-20 -right-16 -z-10 h-64 w-64 rounded-full bg-violet-400/40 blur-3xl" />
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div className="max-w-xl">
            <p className="text-sm font-medium text-indigo-100">Overview</p>
            <h1 className="mt-1 text-2xl font-bold tracking-tight sm:text-3xl">
              Your AI answer audits at a glance
            </h1>
            <p className="mt-2 text-indigo-100">
              Queue runs, follow their progress and clear the review queue.
            </p>
          </div>
          <div className="flex w-full flex-wrap gap-3 sm:w-auto">
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
          label="Latest run"
          value={latest ? humanize(latest.status) : '–'}
          hint={latest ? formatDateTime(latest.created_at) : 'No runs yet'}
          icon="runs"
          tone="indigo"
        />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <Card
          className="lg:col-span-2"
          title="Recent runs"
          description="The five newest audit runs."
          bodyClassName=""
          actions={
            <Link
              to={PATHS.runs}
              className="group inline-flex items-center gap-1 text-sm font-medium text-indigo-700 transition-colors hover:text-indigo-500"
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

        <Card title="Quick actions">
          <ul className="-mx-2 space-y-1">
            {QUICK_ACTIONS.map((action) => (
              <li key={action.to}>
                <Link
                  to={action.to}
                  className="group flex items-center gap-3 rounded-xl p-3 transition-colors duration-150 hover:bg-slate-50"
                >
                  <div className="flex h-10 w-10 flex-none items-center justify-center rounded-lg bg-indigo-50 text-indigo-600 ring-1 ring-indigo-100 transition-colors group-hover:bg-indigo-600 group-hover:text-white group-hover:ring-indigo-600">
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
