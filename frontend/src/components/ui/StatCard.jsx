import Icon from './Icon'

// Each tone: the icon tile gradient, the soft glow in the corner and the progress bar colour.
const TONES = {
  indigo: { tile: 'from-indigo-500 to-violet-600 shadow-indigo-500/40', glow: 'bg-indigo-400/20', bar: 'from-indigo-500 to-violet-500' },
  green: { tile: 'from-emerald-500 to-teal-600 shadow-emerald-500/40', glow: 'bg-emerald-400/20', bar: 'from-emerald-500 to-teal-500' },
  red: { tile: 'from-rose-500 to-pink-600 shadow-rose-500/40', glow: 'bg-rose-400/20', bar: 'from-rose-500 to-pink-500' },
  amber: { tile: 'from-amber-400 to-orange-500 shadow-amber-500/40', glow: 'bg-amber-300/25', bar: 'from-amber-400 to-orange-500' },
  slate: { tile: 'from-slate-500 to-slate-700 shadow-slate-500/40', glow: 'bg-slate-300/25', bar: 'from-slate-400 to-slate-600' },
}

/**
 * One headline number. `progress` (0–1, optional) draws a bar under it — only pass a
 * share that comes from the API's own numbers (for example verified / total answers).
 */
export default function StatCard({ label, value, hint, icon, tone = 'indigo', progress }) {
  const style = TONES[tone]
  const pct = progress === null || progress === undefined ? null : Math.max(0, Math.min(1, progress)) * 100
  return (
    <div className="surface group relative overflow-hidden p-5 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg">
      <div
        className={`pointer-events-none absolute -top-10 -right-10 h-32 w-32 rounded-full blur-2xl transition-opacity duration-300 group-hover:opacity-100 ${style.glow} opacity-70`}
        aria-hidden
      />
      <div className="relative flex items-start justify-between gap-3">
        <p className="text-sm font-medium text-slate-500">{label}</p>
        {icon ? (
          <div
            className={`flex h-10 w-10 flex-none items-center justify-center rounded-xl bg-gradient-to-br text-white shadow-lg ${style.tile}`}
          >
            <Icon name={icon} className="h-5 w-5" />
          </div>
        ) : null}
      </div>
      <p className="relative mt-1 truncate font-display text-[28px] leading-9 font-bold tracking-tight text-slate-900 tabular-nums">
        {value}
      </p>
      {pct !== null ? (
        <div className="relative mt-3 h-1.5 overflow-hidden rounded-full bg-slate-100" aria-hidden>
          <div
            className={`h-full rounded-full bg-gradient-to-r transition-[width] duration-700 ease-out ${style.bar}`}
            style={{ width: `${pct}%` }}
          />
        </div>
      ) : null}
      {hint ? <p className="relative mt-2 text-xs leading-5 text-slate-500">{hint}</p> : null}
    </div>
  )
}
