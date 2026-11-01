import { useEffect } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { useNavigate } from 'react-router-dom'
import { BudgetBar, ProviderChips, RunIdCell } from '../components/domain/RunCells'
import { RunStatusBadge } from '../components/domain/StatusBadges'
import { Button, ButtonLink } from '../components/ui/Button'
import Card from '../components/ui/Card'
import EmptyState from '../components/ui/EmptyState'
import ErrorBanner from '../components/ui/ErrorBanner'
import Icon from '../components/ui/Icon'
import { INPUT_CLASSES, SELECT_CLASSES } from '../components/ui/inputStyles'
import PageHeader from '../components/ui/PageHeader'
import Pagination from '../components/ui/Pagination'
import LoadingState from '../components/ui/LoadingState'
import Table from '../components/ui/Table'
import { fetchRuns, setRunsFilter, setRunsOffset } from '../features/runs/runsSlice'
import { PATHS, runPath } from '../routes/paths'
import { RUN_STATUSES } from '../utils/constants'
import { formatDateTime, humanize } from '../utils/format'

export default function RunsPage() {
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const { items, status, error, filter, offset, limit } = useSelector((state) => state.runs.list)

  const load = () => dispatch(fetchRuns({ status: filter, limit, offset }))

  useEffect(() => {
    dispatch(fetchRuns({ status: filter, limit, offset }))
  }, [dispatch, filter, limit, offset])

  const columns = [
    { key: 'id', header: 'Run', render: (run) => <RunIdCell run={run} /> },
    { key: 'status', header: 'Status', render: (run) => <RunStatusBadge status={run.status} /> },
    {
      key: 'providers',
      header: 'Assistants',
      render: (run) => <ProviderChips providers={run.config.answer_providers} />,
    },
    {
      key: 'repeats',
      header: 'Repeats',
      className: 'text-center',
      render: (run) => (
        <span className="inline-flex h-6 min-w-6 items-center justify-center rounded-md bg-slate-100 px-1.5 text-xs font-semibold text-slate-700">
          ×{run.config.repeats}
        </span>
      ),
    },
    {
      key: 'calls',
      header: 'Model calls',
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
      <PageHeader
        eyebrow="Workspace"
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
        icon={<Icon name="runs" className="h-5 w-5" />}
        actions={
          <>
            <label htmlFor="status-filter" className="sr-only">
              Filter by status
            </label>
            <div className="flex items-center gap-2">
              <div className="w-44">
                <select
                  id="status-filter"
                  value={filter}
                  onChange={(event) => dispatch(setRunsFilter(event.target.value))}
                  className={SELECT_CLASSES}
                >
                  <option value="">All statuses</option>
                  {RUN_STATUSES.map((value) => (
                    <option key={value} value={value}>
                      {humanize(value)}
                    </option>
                  ))}
                </select>
              </div>
              <Button variant="secondary" onClick={load} aria-label="Refresh">
                <Icon name="refresh" className="h-4 w-4" />
              </Button>
            </div>
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
