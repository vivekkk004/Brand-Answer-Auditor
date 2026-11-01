import { useEffect } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { Link, useNavigate } from 'react-router-dom'
import { RunStatusBadge } from '../components/domain/StatusBadges'
import { ButtonLink } from '../components/ui/Button'
import Card from '../components/ui/Card'
import EmptyState from '../components/ui/EmptyState'
import ErrorBanner from '../components/ui/ErrorBanner'
import Icon from '../components/ui/Icon'
import PageHeader from '../components/ui/PageHeader'
import Spinner from '../components/ui/Spinner'
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
        <Link to={runPath(run.id)} className="font-mono text-xs font-medium text-indigo-700 hover:underline">
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
      <PageHeader
        title="Overview"
        description="Your audit runs and review work at a glance."
        actions={
          <ButtonLink to={PATHS.newRun}>
            <Icon name="plus" className="h-4 w-4" />
            New audit run
          </ButtonLink>
        }
      />

      <div className="grid gap-4 sm:grid-cols-3">
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
            <Link to={PATHS.runs} className="text-sm font-medium text-indigo-700 hover:underline">
              View all
            </Link>
          }
        >
          {(recent.status === 'idle' || recent.status === 'loading') && !recent.items.length ? (
            <div className="p-6">
              <Spinner label="Loading runs…" />
            </div>
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
          <ul className="space-y-2">
            {QUICK_ACTIONS.map((action) => (
              <li key={action.to}>
                <Link
                  to={action.to}
                  className="group flex gap-3 rounded-lg p-3 transition-colors hover:bg-slate-50"
                >
                  <div className="flex h-9 w-9 flex-none items-center justify-center rounded-lg bg-indigo-50 text-indigo-600">
                    <Icon name={action.icon} className="h-5 w-5" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-slate-900 group-hover:text-indigo-700">
                      {action.title}
                    </p>
                    <p className="text-xs text-slate-500">{action.text}</p>
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </>
  )
}
