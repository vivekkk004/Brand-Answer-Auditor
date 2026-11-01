import { Link } from 'react-router-dom'

/** The brand mark: a check in an indigo-to-violet tile, plus the product name. */
export function LogoMark({ className = 'h-8 w-8' }) {
  return (
    <svg viewBox="0 0 32 32" className={`flex-none ${className}`} aria-hidden>
      <defs>
        <linearGradient id="logo-gradient" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#4f46e5" />
          <stop offset="1" stopColor="#7c3aed" />
        </linearGradient>
      </defs>
      <rect width="32" height="32" rx="9" fill="url(#logo-gradient)" />
      <path
        d="M9 16.5l4.5 4.5L23 11.5"
        fill="none"
        stroke="#fff"
        strokeWidth="3"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

export default function Logo({ to = '/', compact = false }) {
  return (
    <Link to={to} className="inline-flex items-center gap-2.5" aria-label="Brand Answer Auditor home">
      <LogoMark />
      {compact ? null : (
        // On very narrow phones only the mark is shown, so the header never overflows.
        <span className="hidden text-[15px] font-semibold tracking-tight whitespace-nowrap text-slate-900 min-[420px]:inline">
          Brand Answer <span className="text-gradient">Auditor</span>
        </span>
      )}
    </Link>
  )
}
