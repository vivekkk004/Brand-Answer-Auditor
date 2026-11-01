import { LABEL_BAR } from '../../utils/constants'
import { formatPercent, humanize } from '../../utils/format'

const ORDER = ['supported', 'contradicted', 'unknown']

/** One stacked bar of claim labels, with a legend that shows counts and shares. */
export default function LabelShareBar({ labels, total }) {
  if (!total) {
    return <p className="text-sm text-slate-500">No claims have been verified yet.</p>
  }
  return (
    <div>
      <div className="flex h-3 w-full overflow-hidden rounded-full bg-slate-100">
        {ORDER.map((label) =>
          labels[label]?.share ? (
            <div
              key={label}
              className={LABEL_BAR[label]}
              style={{ width: `${labels[label].share * 100}%` }}
              title={`${humanize(label)}: ${labels[label].count}`}
            />
          ) : null,
        )}
      </div>
      <dl className="mt-4 grid grid-cols-3 gap-4">
        {ORDER.map((label) => (
          <div key={label}>
            <dt className="flex items-center gap-2 text-xs font-medium text-slate-500">
              <span className={`h-2 w-2 rounded-full ${LABEL_BAR[label]}`} />
              {humanize(label)}
            </dt>
            <dd className="mt-1 text-lg font-semibold text-slate-900">
              {labels[label]?.count ?? 0}
              <span className="ml-1.5 text-xs font-normal text-slate-500">
                {formatPercent(labels[label]?.share)}
              </span>
            </dd>
          </div>
        ))}
      </dl>
    </div>
  )
}
