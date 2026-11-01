import { useEffect, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { Link } from 'react-router-dom'
import { LabelBadge, ReviewStatusBadge } from '../components/domain/StatusBadges'
import { Button } from '../components/ui/Button'
import Card from '../components/ui/Card'
import EmptyState from '../components/ui/EmptyState'
import ErrorBanner from '../components/ui/ErrorBanner'
import { INPUT_CLASSES } from '../components/ui/inputStyles'
import PageHeader from '../components/ui/PageHeader'
import Pagination from '../components/ui/Pagination'
import Spinner from '../components/ui/Spinner'
import {
  clearDecideError,
  decideReviewItem,
  fetchReviewItems,
  setReviewFilter,
  setReviewOffset,
} from '../features/review/reviewSlice'
import { answerPath } from '../routes/paths'
import { REVIEW_STATUSES } from '../utils/constants'
import { formatDateTime, humanize } from '../utils/format'

const EMPTY_TEXT = {
  open: { title: 'Nothing to review', text: 'Contradicted claims appear here as soon as they are found.' },
  confirmed: { title: 'No confirmed items', text: 'Items you confirm as wrong will be listed here.' },
  dismissed: { title: 'No dismissed items', text: 'Items you dismiss will be listed here.' },
}

function ReviewItemCard({ item, pending, decideError, onDecide }) {
  const [note, setNote] = useState('')
  const { claim } = item

  return (
    <li className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <ReviewStatusBadge status={item.status} />
          <LabelBadge label={claim.label} />
          <span className="text-xs font-medium text-slate-500">
            {claim.product || claim.brand_id} · {humanize(claim.attribute)}
          </span>
        </div>
        <span className="text-xs text-slate-400">Found {formatDateTime(item.created_at)}</span>
      </div>

      <blockquote className="mt-4 border-l-4 border-rose-300 pl-4 text-slate-900">“{claim.quote}”</blockquote>
      <p className="mt-3 text-sm text-slate-600">
        <span className="font-medium text-slate-700">Agent’s reason: </span>
        {claim.rationale}
      </p>
      <div className="mt-3 flex flex-wrap items-center gap-1.5">
        <span className="text-xs text-slate-500">Cited facts:</span>
        {claim.fact_ids.map((factId) => (
          <code key={factId} className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-600">
            {factId}
          </code>
        ))}
        <Link to={answerPath(item.answer_id)} className="ml-auto text-sm font-medium text-indigo-700 hover:underline">
          Open answer
        </Link>
      </div>

      {item.status === 'open' ? (
        <div className="mt-5 border-t border-slate-100 pt-4">
          <label htmlFor={`note-${item.id}`} className="text-xs font-medium text-slate-600">
            Note (optional)
          </label>
          <textarea
            id={`note-${item.id}`}
            rows={2}
            maxLength={2000}
            className={`${INPUT_CLASSES} mt-1`}
            placeholder="Why you confirmed or dismissed it"
            value={note}
            onChange={(event) => setNote(event.target.value)}
          />
          {decideError ? (
            <div className="mt-3">
              <ErrorBanner
                error={decideError}
                title={decideError.status === 409 ? 'Already decided' : 'Could not save the decision'}
              />
            </div>
          ) : null}
          <div className="mt-3 flex flex-wrap justify-end gap-2">
            <Button variant="secondary" disabled={pending} onClick={() => onDecide('dismissed', note)}>
              Dismiss — the claim is fine
            </Button>
            <Button variant="danger" loading={pending} onClick={() => onDecide('confirmed', note)}>
              Confirm — the claim is wrong
            </Button>
          </div>
        </div>
      ) : (
        <div className="mt-4 rounded-lg bg-slate-50 p-3 text-sm text-slate-600">
          Decided {formatDateTime(item.resolved_at)}
          {item.note ? <> — “{item.note}”</> : null}
        </div>
      )}
    </li>
  )
}

export default function ReviewQueuePage() {
  const dispatch = useDispatch()
  const { items, status, error, filter, offset, limit, decide } = useSelector((state) => state.review)

  const load = () => dispatch(fetchReviewItems({ status: filter, limit, offset }))

  useEffect(() => {
    dispatch(fetchReviewItems({ status: filter, limit, offset }))
  }, [dispatch, filter, limit, offset])

  async function handleDecide(item, decision, note) {
    const result = await dispatch(decideReviewItem({ id: item.id, decision, note }))
    // 409: someone else decided it first. Reload so the list shows the real state.
    if (decideReviewItem.rejected.match(result) && result.payload?.status === 409) {
      dispatch(fetchReviewItems({ status: filter, limit, offset }))
    }
  }

  const empty = EMPTY_TEXT[filter]

  return (
    <>
      <PageHeader
        title="Review queue"
        description="Every contradicted claim is checked by a person before anyone acts on it. A decision is final."
      />

      <div className="mb-4 flex gap-1 rounded-lg bg-slate-100 p-1 sm:inline-flex" role="tablist" aria-label="Status">
        {REVIEW_STATUSES.map((value) => (
          <button
            key={value}
            type="button"
            role="tab"
            aria-selected={filter === value}
            onClick={() => {
              dispatch(clearDecideError())
              dispatch(setReviewFilter(value))
            }}
            className={`flex-1 rounded-md px-4 py-1.5 text-sm font-medium transition-colors sm:flex-none ${
              filter === value ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            {humanize(value)}
          </button>
        ))}
      </div>

      {status === 'failed' ? (
        <ErrorBanner error={error} title="Could not load the review queue" onRetry={load} />
      ) : (status === 'idle' || status === 'loading') && !items.length ? (
        <Spinner label="Loading review items…" />
      ) : items.length ? (
        <>
          <ul className="space-y-4">
            {items.map((item) => (
              <ReviewItemCard
                key={item.id}
                item={item}
                pending={decide.pendingId === item.id}
                decideError={decide.itemId === item.id ? decide.error : null}
                onDecide={(decision, note) => handleDecide(item, decision, note)}
              />
            ))}
          </ul>
          <div className="mt-4 rounded-xl border border-slate-200 bg-white">
            <Pagination
              offset={offset}
              limit={limit}
              count={items.length}
              disabled={status === 'loading'}
              onChange={(next) => dispatch(setReviewOffset(next))}
            />
          </div>
        </>
      ) : (
        <Card>
          <EmptyState icon="review" title={empty.title} description={empty.text} />
        </Card>
      )}
    </>
  )
}
