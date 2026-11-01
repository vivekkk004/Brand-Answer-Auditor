import { useEffect, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { useParams } from 'react-router-dom'
import AgentConversation from '../components/domain/AgentConversation'
import ClaimList from '../components/domain/ClaimList'
import HighlightedAnswer from '../components/domain/HighlightedAnswer'
import { AnswerStatusBadge } from '../components/domain/StatusBadges'
import Card from '../components/ui/Card'
import DescriptionList from '../components/ui/DescriptionList'
import EmptyState from '../components/ui/EmptyState'
import ErrorBanner from '../components/ui/ErrorBanner'
import Icon from '../components/ui/Icon'
import LoadingState from '../components/ui/LoadingState'
import PageHeader from '../components/ui/PageHeader'
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
  return <DescriptionList items={rows} />
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
          <LoadingState label="Loading answer…" />
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
        eyebrow={answer.run_id ? 'Answer from an audit run' : 'Submitted answer'}
        title={
          <span className="flex flex-wrap items-center gap-3">
            <span className="font-mono">{shortId(answer.id)}</span>
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
          <Card
            title="Answer text"
            description="Claims are highlighted by label. Click one to find it in the list."
            icon={<Icon name="search" className="h-5 w-5" />}
          >
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
          <Card
            title="Claims"
            description={`${answer.claims.length} claim(s)`}
            icon={<Icon name="verify" className="h-5 w-5" />}
          >
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
          <Card title="Brands mentioned" icon={<Icon name="sparkles" className="h-5 w-5" />}>
            {answer.brands_mentioned.length ? (
              <div className="flex flex-wrap gap-2">
                {answer.brands_mentioned.map((brand) => (
                  <span
                    key={brand}
                    className="inline-flex items-center gap-2 rounded-lg bg-slate-50 py-1 pr-3 pl-1 text-sm font-semibold text-slate-800 ring-1 ring-slate-200 ring-inset"
                  >
                    <span className="flex h-6 w-6 items-center justify-center rounded-md bg-gradient-to-br from-slate-700 to-slate-900 text-xs font-bold text-white uppercase">
                      {brand.slice(0, 1)}
                    </span>
                    {humanize(brand)}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-sm text-slate-500">No catalogue brand was mentioned.</p>
            )}
          </Card>
          <Card title="Details" icon={<Icon name="info" className="h-5 w-5" />}>
            <Details answer={answer} />
          </Card>
        </div>
      </div>

      <Card
        className="mt-6"
        title="Agent conversation"
        description="Every message, tool call and tool result the verifier exchanged — the trace for debugging."
        icon={<Icon name="tool" className="h-5 w-5" />}
      >
        <details className="group">
          <summary className="inline-flex cursor-pointer list-none items-center gap-1.5 rounded-lg text-sm font-medium text-indigo-700 transition-colors select-none hover:text-indigo-500 [&::-webkit-details-marker]:hidden">
            <Icon name="chevronDown" className="h-4 w-4 -rotate-90 transition-transform duration-200 group-open:rotate-0" />
            {answer.exchanges?.length
              ? `Show ${answer.exchanges.length} step(s)`
              : 'No conversation recorded'}
          </summary>
          <div className="animate-page-in mt-5">
            <AgentConversation exchanges={answer.exchanges} />
          </div>
        </details>
      </Card>
    </>
  )
}
