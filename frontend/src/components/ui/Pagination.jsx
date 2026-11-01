import { Button } from './Button'

/**
 * Previous / Next paging. The API returns no total count, so "Next" is offered only
 * when the current page came back full.
 */
export default function Pagination({ offset, limit, count, onChange, disabled, boxed = false }) {
  const hasPrevious = offset > 0
  const hasNext = count === limit
  if (!hasPrevious && !hasNext) return null
  return (
    <nav
      className={`flex items-center justify-between gap-3 px-5 py-3 sm:px-6 ${boxed ? 'surface mt-4' : 'border-t border-slate-100'}`}
      aria-label="Pagination"
    >
      <p className="text-sm text-slate-500 tabular-nums">
        Showing {count ? offset + 1 : 0}–{offset + count}
      </p>
      <div className="flex gap-2">
        <Button
          variant="secondary"
          size="sm"
          disabled={!hasPrevious || disabled}
          onClick={() => onChange(Math.max(0, offset - limit))}
        >
          Previous
        </Button>
        <Button
          variant="secondary"
          size="sm"
          disabled={!hasNext || disabled}
          onClick={() => onChange(offset + limit)}
        >
          Next
        </Button>
      </div>
    </nav>
  )
}
