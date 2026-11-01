import Icon from './Icon'

const TONES = {
  indigo: { tile: 'from-indigo-500 to-violet-500', accent: 'bg-indigo-500' },
  green: { tile: 'from-emerald-500 to-teal-500', accent: 'bg-emerald-500' },
  red: { tile: 'from-rose-500 to-pink-500', accent: 'bg-rose-500' },
  amber: { tile: 'from-amber-400 to-orange-500', accent: 'bg-amber-500' },
  slate: { tile: 'from-slate-400 to-slate-500', accent: 'bg-slate-400' },
}

export default function StatCard({ label, value, hint, icon, tone = 'indigo' }) {
  const style = TONES[tone]
  return (
    <div className="group relative overflow-hidden rounded-2xl border border-slate-200/80 bg-white p-5 shadow-card transition-shadow hover:shadow-md">
      <div className={`absolute inset-x-0 top-0 h-0.5 ${style.accent} opacity-70`} />
      <div className="flex items-start gap-4">
        {icon ? (
          <div
            className={`flex h-11 w-11 flex-none items-center justify-center rounded-xl bg-gradient-to-br text-white shadow-sm ${style.tile}`}
          >
            <Icon name={icon} />
          </div>
        ) : null}
        <div className="min-w-0">
          <p className="text-sm font-medium text-slate-500">{label}</p>
          <p className="mt-1 truncate text-2xl font-bold tracking-tight text-slate-900">{value}</p>
          {hint ? <p className="mt-1 text-xs text-slate-500">{hint}</p> : null}
        </div>
      </div>
    </div>
  )
}
