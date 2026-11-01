import { useState } from 'react'
import { formatPercent } from '../../utils/format'
import EmptyState from '../ui/EmptyState'
import SegmentedControl from '../ui/SegmentedControl'
import Table from '../ui/Table'
import ConfidenceBar from './ConfidenceBar'

const ALL = 'all'

/**
 * Inclusion per brand: k of n answers named it, the rate, and the 95% Wilson interval.
 * The API gives one row per brand per model plus an "all models" row (provider = null).
 */
export default function InclusionTable({ inclusion }) {
  const rows = inclusion || []
  const models = [...new Set(rows.filter((row) => row.model).map((row) => row.model))]
  const [view, setView] = useState(ALL)

  const visible = rows
    .filter((row) => (view === ALL ? row.provider === null : row.model === view))
    .sort((a, b) => (b.rate ?? -1) - (a.rate ?? -1))

  if (!rows.length) {
    return <EmptyState icon="chart" title="No inclusion data yet" />
  }

  const columns = [
    { key: 'brand_id', header: 'Brand', className: 'font-medium text-slate-900' },
    { key: 'kn', header: 'Named in', className: 'whitespace-nowrap', render: (row) => `${row.k} of ${row.n}` },
    {
      key: 'rate',
      header: 'Rate',
      render: (row) => <span className="font-semibold text-slate-900">{formatPercent(row.rate)}</span>,
    },
    {
      key: 'ci',
      header: '95% interval',
      className: 'w-2/5',
      render: (row) => (
        <div className="flex items-center gap-3">
          <ConfidenceBar rate={row.rate} low={row.ci_low} high={row.ci_high} />
          <span className="w-28 flex-none text-xs whitespace-nowrap text-slate-500">
            {row.ci_low === null ? '' : `${formatPercent(row.ci_low)} – ${formatPercent(row.ci_high)}`}
          </span>
        </div>
      ),
    },
  ]

  return (
    <div>
      {models.length > 1 ? (
        <div className="border-b border-slate-100 px-5 py-3 sm:px-6">
          <SegmentedControl
            label="Model"
            size="sm"
            className="sm:inline-flex"
            options={[ALL, ...models].map((option) => ({
              value: option,
              label: option === ALL ? 'All models' : option,
            }))}
            value={view}
            onChange={setView}
          />
        </div>
      ) : null}
      <Table columns={columns} rows={visible} rowKey={(row) => `${row.brand_id}-${row.model}`} />
    </div>
  )
}
