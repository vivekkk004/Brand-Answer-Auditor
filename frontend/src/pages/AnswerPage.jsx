import { useEffect, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { useParams } from 'react-router-dom'
import AgentConversation from '../components/domain/AgentConversation'
import ClaimList from '../components/domain/ClaimList'
import HighlightedAnswer from '../components/domain/HighlightedAnswer'
import { AnswerStatusBadge } from '../components/domain/StatusBadges'
import Badge from '../components/ui/Badge'
import Card from '../components/ui/Card'
import EmptyState from '../components/ui/EmptyState'
import ErrorBanner from '../components/ui/ErrorBanner'
import PageHeader from '../components/ui/PageHeader'
import Spinner from '../components/ui/Spinner'
import { fetchAnswer, selectAnswerById } from '../features/answers/answersSlice'
import { PATHS, runPath } from '../routes/paths'
import { EMPTY, formatDateTime, formatMs, formatNumber, humanize, shortId } from '../utils/format'

function tokensText(usage) {
  if (!usage) return EMPTY
  return `${formatNumber(usage.input)} in · ${formatNumber(usage.output)} out`
}

function Details({ answer }) {
  const rows = [
    ['Market', answer.market || EMPTY],
    ['Answer model', answer.model ? `${humanize(answer.provider)} · ${answer.model}` : 'Submitted text'],
    ['Prompt', answer.prompt_id ? `${answer.prompt_id} (repeat ${answer.repeat_index + 1})` : EMPTY],
    ['Verifier model', answer.verifier_model || EMPTY],
    ['Agent prompt', answer.prompt_version || EMPTY],
    ['Agent turns', answer.verification_turns ?? EMPTY],
    ['Verification time', formatMs(answer.verification_latency_ms)],
    ['Timed out', answer.timed_out ? 'Yes' : 'No'],
    ['Generation tokens', tokensText(answer.usage?.generation)],
    ['Verification tokens', tokensText(answer.usage?.verification)],
    ['Created', formatDateTime(answer.created_at)],
  ]
  return (
    <dl className="divide-y divide-slate-100 text-sm">
      {rows.map(([label, value]) => (
        <div key={label} className="flex justify-between gap-4 py-2">
          <dt className="text-slate-500">{label}</dt>
          <dd className="text-right font-medium text-slate-900">{value}</dd>
        </div>
      ))}
    </dl>
  )
}

export default function AnswerPage() {
  const { answerId } = useParams()
  const dispatch = useDispatch()
  const answer = useSelector(selectAnswerById(answerId))
  const { status, error } = useSelector((state) => state.answers)
  const [activeClaimId, setActiveClaimId] = useState(null)

  useEffect(() => {
    dispatch(fetchAnswer(answerId))
  }, [dispatch, answerId])

  if (!answer) {
    return (
      <>
        <PageHeader title="Answer" back={{ to: PATHS.verify, label: 'Verify answer' }} />
        {status === 'failed' ? (
          <ErrorBanner error={error} title="Could not load this answer" onRetry={() => dispatch(fetchAnswer(answerId))} />
        ) : (
          <Spinner label="Loading answer…" />
        )}
      </>
    )
  }

  const back = answer.run_id
    ? { to: runPath(answer.run_id), label: 'Audit run' }
    : { to: PATHS.verify, label: 'Verify answer' }

  return (
    <>
      <PageHeader
        title={
          <span className="flex flex-wrap items-center gap-3">
            Answer <span className="font-mono text-xl text-slate-500">{shortId(answer.id)}</span>
            <AnswerStatusBadge status={answer.status} />
          </span>
        }
        back={back}
      />

      {answer.error_type ? (
        <div className="mb-6">
          <ErrorBanner
            error={{ message: answer.error_message, code: `error type: ${answer.error_type}` }}
            title={`This answer failed (${humanize(answer.status)})`}
          />
        </div>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Card title="Answer text" description="Claims are highlighted by label. Click one to find it in the list.">
            {answer.text ? (
              <HighlightedAnswer
                text={answer.text}
                claims={answer.claims}
                activeClaimId={activeClaimId}
                onSelectClaim={setActiveClaimId}
              />
            ) : (
              <p className="text-sm text-slate-500">No text was received from the answer model.</p>
            )}
          </Card>
          <Card title="Claims" description={`${answer.claims.length} claim(s)`}>
            {answer.status === 'verified' ? (
              <ClaimList claims={answer.claims} activeClaimId={activeClaimId} onSelectClaim={setActiveClaimId} />
            ) : (
              // A failed answer stores no claims (all or nothing), so "no claims" would mislead.
              <EmptyState
                icon="alert"
                title="Not verified"
                description={
                  answer.status === 'pending'
                    ? 'This answer is waiting to be verified.'
                    : 'Verification did not complete, so no claims were saved. See the error above.'
                }
              />
            )}
          </Card>
        </div>

        <div className="space-y-6">
          <Card title="Brands mentioned">
            {answer.brands_mentioned.length ? (
              <div className="flex flex-wrap gap-2">
                {answer.brands_mentioned.map((brand) => (
                  <Badge key={brand} tone="indigo">
                    {brand}
                  </Badge>
                ))}
              </div>
            ) : (
              <p className="text-sm text-slate-500">No catalogue brand was mentioned.</p>
            )}
          </Card>
          <Card title="Details">
            <Details answer={answer} />
          </Card>
        </div>
      </div>

      <Card
        className="mt-6"
        title="Agent conversation"
        description="Every message, tool call and tool result the verifier exchanged — the trace for debugging."
      >
        <details className="group">
          <summary className="cursor-pointer text-sm font-medium text-indigo-700 select-none hover:underline">
            {answer.exchanges?.length
              ? `Show ${answer.exchanges.length} step(s)`
              : 'No conversation recorded'}
          </summary>
          <div className="mt-5">
            <AgentConversation exchanges={answer.exchanges} />
          </div>
        </details>
      </Card>
    </>
  )
}
