import { useEffect } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { Link, useNavigate } from 'react-router-dom'
import { RunStatusBadge } from '../components/domain/StatusBadges'
import { Button, ButtonLink } from '../components/ui/Button'
import Card from '../components/ui/Card'
import EmptyState from '../components/ui/EmptyState'
import ErrorBanner from '../components/ui/ErrorBanner'
import Icon from '../components/ui/Icon'
import { INPUT_CLASSES } from '../components/ui/inputStyles'
import PageHeader from '../components/ui/PageHeader'
import Pagination from '../components/ui/Pagination'
import LoadingState from '../components/ui/LoadingState'
import Table from '../components/ui/Table'
import { fetchRuns, setRunsFilter, setRunsOffset } from '../features/runs/runsSlice'
import { PATHS, runPath } from '../routes/paths'
import { RUN_STATUSES } from '../utils/constants'
import { formatDateTime, formatNumber, humanize, shortId } from '../utils/format'

export default function RunsPage() {
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const { items, status, error, filter, offset, limit } = useSelector((state) => state.runs.list)

  const load = () => dispatch(fetchRuns({ status: filter, limit, offset }))

  useEffect(() => {
    dispatch(fetchRuns({ status: filter, limit, offset }))
  }, [dispatch, filter, limit, offset])

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
      key: 'providers',
      header: 'Assistants',
      render: (run) => run.config.answer_providers?.map(humanize).join(', '),
    },
    { key: 'repeats', header: 'Repeats', className: 'text-right', render: (run) => run.config.repeats },
    {
      key: 'calls',
      header: 'Model calls',
      className: 'whitespace-nowrap text-right',
      render: (run) => `${formatNumber(run.model_calls)} / ${formatNumber(run.max_model_calls)}`,
    },
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
        title="Audit runs"
        description="Every run you queued, newest first."
        actions={
          <ButtonLink to={PATHS.newRun}>
            <Icon name="plus" className="h-4 w-4" />
            New audit run
          </ButtonLink>
        }
      />

      <Card
        bodyClassName=""
        title="Runs"
        description="Click a row to open the run."
        actions={
          <>
            <label htmlFor="status-filter" className="sr-only">
              Filter by status
            </label>
            <select
              id="status-filter"
              value={filter}
              onChange={(event) => dispatch(setRunsFilter(event.target.value))}
              className={`${INPUT_CLASSES} w-44`}
            >
              <option value="">All statuses</option>
              {RUN_STATUSES.map((value) => (
                <option key={value} value={value}>
                  {humanize(value)}
                </option>
              ))}
            </select>
            <Button variant="secondary" onClick={load} aria-label="Refresh">
              <Icon name="refresh" className="h-4 w-4" />
            </Button>
          </>
        }
      >
        {status === 'failed' ? (
          <div className="p-5 sm:p-6">
            <ErrorBanner error={error} title="Could not load runs" onRetry={load} />
          </div>
        ) : (status === 'idle' || status === 'loading') && !items.length ? (
          <LoadingState label="Loading runs…" />
        ) : (
          <>
            <Table
              columns={columns}
              rows={items}
              onRowClick={(run) => navigate(runPath(run.id))}
              empty={
                <EmptyState
                  title={filter ? `No ${filter} runs` : 'No audit runs yet'}
                  description={
                    filter
                      ? 'Try another status filter.'
                      : 'Queue a run to ask assistants your prompts and verify their answers.'
                  }
                  action={filter ? null : <ButtonLink to={PATHS.newRun}>New audit run</ButtonLink>}
                />
              }
            />
            <Pagination
              offset={offset}
              limit={limit}
              count={items.length}
              disabled={status === 'loading'}
              onChange={(next) => dispatch(setRunsOffset(next))}
            />
          </>
        )}
      </Card>
    </>
  )
}
