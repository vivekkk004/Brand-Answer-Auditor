import { useId } from 'react'

/**
 * A ring that fills to `value / max`, with the share in the middle. Used for the model-call
 * budget, so both numbers come straight from the run.
 */
export default function ProgressRing({ value, max, size = 112, stroke = 10, label, className = '' }) {
  const gradientId = useId()
  const share = max ? Math.max(0, Math.min(1, value / max)) : 0
  const radius = (size - stroke) / 2
  const circumference = 2 * Math.PI * radius
  return (
    <div className={`relative flex-none ${className}`} style={{ width: size, height: size }}>
      <svg viewBox={`0 0 ${size} ${size}`} className="-rotate-90" role="img" aria-label={label}>
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#818cf8" />
            <stop offset="1" stopColor="#c084fc" />
          </linearGradient>
        </defs>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeOpacity="0.15"
          strokeWidth={stroke}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={`url(#${gradientId})`}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference * (1 - share)}
          className="transition-[stroke-dashoffset] duration-1000 ease-out"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="font-display text-2xl font-bold tabular-nums">{Math.round(share * 100)}%</span>
        <span className="text-[11px] font-medium opacity-60">used</span>
      </div>
    </div>
  )
}
