import { formatPercent } from '../../utils/format'

/**
 * A 0–100% track with the 95% Wilson interval shaded and the observed rate as a dot.
 * A wide band means "few answers, the true rate could be anywhere in here".
 */
export default function ConfidenceBar({ rate, low, high }) {
  if (rate === null || rate === undefined) {
    return <span className="text-xs text-slate-400">No answers yet</span>
  }
  const lowPct = (low ?? rate) * 100
  const highPct = (high ?? rate) * 100
  return (
    <div
      className="relative h-2 w-full min-w-32 rounded-full bg-slate-100"
      role="img"
      aria-label={`Rate ${formatPercent(rate)}, 95% interval ${formatPercent(low)} to ${formatPercent(high)}`}
    >
      <div
        className="absolute inset-y-0 rounded-full bg-indigo-200 transition-all duration-500 ease-out"
        style={{ left: `${lowPct}%`, width: `${Math.max(highPct - lowPct, 0.5)}%` }}
      />
      <div
        className="absolute top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white bg-indigo-600 shadow transition-all duration-500 ease-out"
        style={{ left: `${rate * 100}%` }}
      />
    </div>
  )
}
