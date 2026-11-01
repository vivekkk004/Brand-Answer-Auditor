import { useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { Link } from 'react-router-dom'
import ClaimList from '../components/domain/ClaimList'
import HighlightedAnswer from '../components/domain/HighlightedAnswer'
import { AnswerStatusBadge, LabelBadge } from '../components/domain/StatusBadges'
import { Button } from '../components/ui/Button'
import Card from '../components/ui/Card'
import ErrorBanner from '../components/ui/ErrorBanner'
import Field from '../components/ui/Field'
import Icon from '../components/ui/Icon'
import { INPUT_CLASSES, SELECT_CLASSES } from '../components/ui/inputStyles'
import PageHeader from '../components/ui/PageHeader'
import { verifyText } from '../features/verify/verifySlice'
import { answerPath } from '../routes/paths'
import { MARKETS, PROMPT_VERSIONS } from '../utils/constants'
import { formatMs } from '../utils/format'

const MAX_LENGTH = 20000

// Uses the fictional demo catalogue (data/demo), so it has facts to check against.
const EXAMPLE_TEXT =
  'The Zentro Air 2 costs ₹6,999 in India. It is rated IPX4 and lasts up to 8 hours with ' +
  'ANC off. It also pairs instantly with any laptop.'

const HOW_IT_WORKS = [
  { title: 'Find the brands', text: 'The agent lists catalogue brands and matches names in the text.' },
  { title: 'Look up facts', text: 'It fetches each brand’s facts with a tool call — nothing from memory.' },
  { title: 'Label each claim', text: 'Every claim is quoted exactly and labelled, citing the facts it read.' },
  { title: 'Validate', text: 'Code checks quotes and citations; invalid output is sent back to fix.' },
]

export default function VerifyPage() {
  const dispatch = useDispatch()
  const { status, result, error } = useSelector((state) => state.verify)
  const [text, setText] = useState('')
  const [market, setMarket] = useState('IN')
  const [promptVersion, setPromptVersion] = useState('v1')
  const [activeClaimId, setActiveClaimId] = useState(null)

  function handleSubmit(event) {
    event.preventDefault()
    setActiveClaimId(null)
    dispatch(verifyText({ text, market, promptVersion }))
  }

  return (
    <>
      <PageHeader
        eyebrow="Verification agent"
        title="Verify an answer"
        description="Paste an AI assistant's answer. The agent extracts its product claims and checks each one against the catalogue."
      />

      <div className="grid gap-6 lg:grid-cols-3">
        <Card
          className="lg:col-span-2"
          title="Answer to check"
          description="Paste the text exactly as the assistant wrote it."
          icon={<Icon name="search" className="h-5 w-5" />}
        >
          <form onSubmit={handleSubmit} className="space-y-5" noValidate>
            <Field
              id="answer-text"
              label="Answer text"
              hint={`${text.length.toLocaleString()} / ${MAX_LENGTH.toLocaleString()} characters`}
              action={
                <button
                  type="button"
                  onClick={() => setText(EXAMPLE_TEXT)}
                  className="inline-flex items-center gap-1.5 rounded-full bg-indigo-50 px-3 py-1 text-xs font-semibold text-indigo-700 ring-1 ring-indigo-200 transition-colors hover:bg-indigo-100"
                >
                  <Icon name="sparkles" className="h-3.5 w-3.5" />
                  Try an example
                </button>
              }
            >
              <textarea
                id="answer-text"
                rows={7}
                maxLength={MAX_LENGTH}
                className={`${INPUT_CLASSES} resize-y leading-6`}
                placeholder="For example: The Zentro Air 2 costs ₹6,999 in India and lasts 8 hours with ANC off."
                value={text}
                onChange={(event) => setText(event.target.value)}
              />
            </Field>
            <div className="flex flex-col gap-4 sm:flex-row sm:flex-wrap sm:items-end">
              <div className="sm:w-48">
                <Field id="market" label="Market">
                  <select
                    id="market"
                    className={SELECT_CLASSES}
                    value={market}
                    onChange={(event) => setMarket(event.target.value)}
                  >
                    {MARKETS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </Field>
              </div>
              <div className="sm:w-64">
                <Field id="prompt-version" label="Agent prompt">
                  <select
                    id="prompt-version"
                    className={SELECT_CLASSES}
                    value={promptVersion}
                    onChange={(event) => setPromptVersion(event.target.value)}
                  >
                    {PROMPT_VERSIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </Field>
              </div>
              <Button
                type="submit"
                className="w-full sm:ml-auto sm:w-auto"
                loading={status === 'loading'}
                disabled={!text.trim()}
              >
                <Icon name="verify" className="h-4 w-4" />
                {status === 'loading' ? 'Verifying…' : 'Verify claims'}
              </Button>
            </div>
          </form>
        </Card>

        <Card title="How verification works" icon={<Icon name="tool" className="h-5 w-5" />}>
          <ol className="relative space-y-5">
            {HOW_IT_WORKS.map((step, index) => (
              <li key={step.title} className="relative flex gap-3">
                {index < HOW_IT_WORKS.length - 1 ? (
                  <span className="absolute top-7 -bottom-4 left-[11px] w-0.5 rounded-full bg-indigo-100" aria-hidden />
                ) : null}
                <span className="relative flex h-6 w-6 flex-none items-center justify-center rounded-full bg-indigo-600 text-xs font-bold text-white ring-4 ring-indigo-50">
                  {index + 1}
                </span>
                <div>
                  <p className="text-sm font-semibold text-slate-900">{step.title}</p>
                  <p className="mt-0.5 text-sm text-slate-500">{step.text}</p>
                </div>
              </li>
            ))}
          </ol>
          <div className="mt-6 flex flex-wrap gap-2 border-t border-slate-100 pt-5">
            <LabelBadge label="supported" />
            <LabelBadge label="contradicted" />
            <LabelBadge label="unknown" />
          </div>
        </Card>
      </div>

      {status === 'failed' ? (
        <div className="mt-6">
          <ErrorBanner error={error} title="Verification did not complete">
            {error?.answerId ? (
              <p className="text-sm text-rose-700">
                The attempt was saved.{' '}
                <Link to={answerPath(error.answerId)} className="font-semibold underline">
                  Open the saved answer
                </Link>{' '}
                to see the error type and the agent conversation.
              </p>
            ) : null}
          </ErrorBanner>
        </div>
      ) : null}

      {status === 'succeeded' && result ? (
        <div className="mt-6 grid gap-6 lg:grid-cols-5">
          <Card
            className="animate-page-in lg:col-span-3"
            title="Answer"
            description={`${result.claims.length} claim(s) · ${result.verification_turns ?? '–'} agent turn(s) · ${formatMs(result.verification_latency_ms)}`}
            actions={
              <>
                <AnswerStatusBadge status={result.status} />
                <Link
                  to={answerPath(result.id)}
                  className="group inline-flex items-center gap-1 text-sm font-medium text-indigo-700 transition-colors hover:text-indigo-500"
                >
                  Full details
                  <Icon name="arrowRight" className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
                </Link>
              </>
            }
          >
            <HighlightedAnswer
              text={result.text}
              claims={result.claims}
              activeClaimId={activeClaimId}
              onSelectClaim={setActiveClaimId}
            />
          </Card>
          <Card className="animate-page-in lg:col-span-2" title="Claims">
            <ClaimList claims={result.claims} activeClaimId={activeClaimId} onSelectClaim={setActiveClaimId} />
          </Card>
        </div>
      ) : null}
    </>
  )
}
