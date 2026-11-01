import { LABEL_BAR, LABEL_ORDER } from '../../utils/constants'
import { formatPercent, humanize } from '../../utils/format'
import Icon from '../ui/Icon'

const LABEL_ICON = { supported: 'check', unknown: 'info', contradicted: 'alert' }

/**
 * Claim labels as one segmented bar plus a legend with counts and shares. The headline is
 * the supported share, read straight from the API's metrics.
 */
export default function LabelShareBar({ labels, total }) {
  if (!total) {
    return <p className="text-sm text-slate-500">No claims have been verified yet.</p>
  }
  const supported = labels.supported?.share
  return (
    <div>
      <div className="flex items-baseline gap-2">
        <p className="font-display text-4xl font-extrabold tracking-tight text-slate-900 tabular-nums">
          {formatPercent(supported)}
        </p>
        <p className="text-sm font-medium text-slate-500">of claims supported by the catalogue</p>
      </div>

      {/* 2px gaps between segments keep the colours apart. */}
      <div className="mt-5 flex h-3 w-full gap-0.5 overflow-hidden rounded-full bg-slate-100">
        {LABEL_ORDER.map((label) =>
          labels[label]?.share ? (
            <div
              key={label}
              className={`${LABEL_BAR[label]} transition-all duration-700 ease-out first:rounded-l-full last:rounded-r-full`}
              style={{ width: `${labels[label].share * 100}%` }}
              title={`${humanize(label)}: ${labels[label].count} (${formatPercent(labels[label].share)})`}
            />
          ) : null,
        )}
      </div>

      <dl className="mt-5 space-y-2">
        {LABEL_ORDER.map((label) => (
          <div key={label} className="flex items-center gap-3 rounded-xl bg-slate-50 px-3 py-2.5 ring-1 ring-slate-100">
            <dt className="flex flex-1 items-center gap-2 text-sm font-medium text-slate-700">
              <span className={`flex h-5 w-5 items-center justify-center rounded-full text-white ${LABEL_BAR[label]}`}>
                <Icon name={LABEL_ICON[label]} className="h-3 w-3" />
              </span>
              {humanize(label)}
            </dt>
            <dd className="flex items-baseline gap-2 tabular-nums">
              <span className="font-display text-lg font-bold text-slate-900">{labels[label]?.count ?? 0}</span>
              <span className="w-12 text-right text-xs font-medium text-slate-500">
                {formatPercent(labels[label]?.share)}
              </span>
            </dd>
          </div>
        ))}
      </dl>
    </div>
  )
}
