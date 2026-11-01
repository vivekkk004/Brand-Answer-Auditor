import { Link } from 'react-router-dom'

export default function Logo({ to = '/', compact = false }) {
  return (
    <Link to={to} className="inline-flex items-center gap-2.5" aria-label="Brand Answer Auditor home">
      <svg viewBox="0 0 32 32" className="h-8 w-8 flex-none" aria-hidden>
        <rect width="32" height="32" rx="8" fill="#4f46e5" />
        <path
          d="M9 16.5l4.5 4.5L23 11.5"
          fill="none"
          stroke="#fff"
          strokeWidth="3"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      {compact ? null : (
        <span className="text-base font-semibold tracking-tight text-slate-900">
          Brand Answer <span className="text-indigo-600">Auditor</span>
        </span>
      )}
    </Link>
  )
}
