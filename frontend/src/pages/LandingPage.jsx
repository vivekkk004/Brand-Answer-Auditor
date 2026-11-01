import HighlightedAnswer from '../components/domain/HighlightedAnswer'
import { LabelBadge } from '../components/domain/StatusBadges'
import { ButtonLink } from '../components/ui/Button'
import { buttonClasses } from '../components/ui/buttonStyles'
import Icon from '../components/ui/Icon'
import { LogoMark } from '../components/ui/Logo'
import { PATHS } from '../routes/paths'

// The product picture is an ILLUSTRATION built from the real components, using the
// fictional demo catalogue (data/demo). It is labelled as such and shows no results.
const SAMPLE_TEXT =
  'The Zentro Air 2 costs ₹6,999 in India. It is rated IPX4 and lasts up to 8 hours ' +
  'with ANC off. It also pairs instantly with any laptop.'

function sampleClaim(id, quote, label, rationale) {
  const start = SAMPLE_TEXT.indexOf(quote)
  return { id, quote, start, end: start + quote.length, label, rationale }
}

const SAMPLE_CLAIMS = [
  sampleClaim('c1', 'The Zentro Air 2 costs ₹6,999 in India', 'contradicted', 'Catalogue price in India is ₹7,999.'),
  sampleClaim('c2', 'It is rated IPX4', 'supported', 'Catalogue lists IPX4.'),
  sampleClaim('c3', 'lasts up to 8 hours with ANC off', 'supported', 'Matches the ANC-off battery fact.'),
  sampleClaim('c4', 'pairs instantly with any laptop', 'unknown', 'No catalogue fact covers pairing.'),
]

const TRACE_STEPS = ['list_known_brands', 'get_brand_facts', 'submit_claims']

const STEPS = [
  {
    icon: 'plus',
    title: 'Queue an audit run',
    text: 'Pick a category, the assistants to ask and how many repeats. Requests are idempotent, so a retry never starts a second run.',
  },
  {
    icon: 'search',
    title: 'Collect answers',
    text: 'A background worker asks every prompt on Gemini and OpenAI and finds brand mentions with deterministic code.',
  },
  {
    icon: 'verify',
    title: 'Verify every claim',
    text: 'The agent quotes each claim exactly; code computes its position and checks every citation against the catalogue.',
  },
  {
    icon: 'review',
    title: 'Review and report',
    text: 'Contradictions go to reviewers; the report shows inclusion, label shares, failures, tokens and cost.',
  },
]

const RELIABILITY = [
  { icon: 'refresh', title: 'Retries done right', text: 'Only rate limits, server errors and timeouts are retried — with exponential backoff and jitter.' },
  { icon: 'shield', title: 'Hard budgets', text: 'Each run has a model-call budget. Verification reserves its worst case first, so a run never overspends.' },
  { icon: 'bolt', title: 'Resumable worker', text: 'Answers are saved one by one. A crashed run is picked up again and never pays for an answer twice.' },
  { icon: 'check', title: 'Strict validation', text: 'Quotes must match the text exactly and facts must have been looked up. Invalid output is never saved.' },
  { icon: 'key', title: 'Isolated clients', text: 'API keys are stored only as hashes, and one client can never see another client’s data.' },
  { icon: 'runs', title: 'Full trace', text: 'Every answer keeps the agent’s whole conversation — each tool call and result — for debugging.' },
]

const FAILURE_TYPES = [
  { name: 'provider', tone: 'bg-sky-50 text-sky-700 ring-sky-200' },
  { name: 'prompt', tone: 'bg-violet-50 text-violet-700 ring-violet-200' },
  { name: 'tool', tone: 'bg-indigo-50 text-indigo-700 ring-indigo-200' },
  { name: 'data', tone: 'bg-amber-50 text-amber-800 ring-amber-200' },
  { name: 'config', tone: 'bg-slate-100 text-slate-700 ring-slate-200' },
  { name: 'code', tone: 'bg-rose-50 text-rose-700 ring-rose-200' },
]

function SectionIntro({ eyebrow, title, text, center = false }) {
  return (
    <div className={`max-w-2xl ${center ? 'mx-auto text-center' : ''}`}>
      <p className="inline-flex items-center gap-2 text-sm font-semibold text-indigo-600">
        <span className="h-px w-6 bg-indigo-300" />
        {eyebrow}
      </p>
      <h2 className="mt-3 text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">{title}</h2>
      {text ? <p className="mt-4 text-lg leading-8 text-slate-600">{text}</p> : null}
    </div>
  )
}

/** The hero's product picture: a browser window with a verified answer, plus floating cards. */
function ProductIllustration() {
  return (
    <div className="relative mx-auto mt-16 max-w-5xl">
      {/* Glow behind the window */}
      <div className="absolute -inset-x-8 -top-8 -bottom-8 -z-10 rounded-[2.5rem] bg-gradient-to-tr from-indigo-200/60 via-violet-200/50 to-sky-200/60 blur-2xl" />

      <div className="overflow-hidden rounded-2xl bg-white shadow-float ring-1 ring-slate-900/10">
        {/* Window chrome */}
        <div className="flex items-center gap-3 border-b border-slate-200/80 bg-slate-50 px-4 py-3">
          <div className="flex gap-1.5">
            <span className="h-3 w-3 rounded-full bg-rose-300" />
            <span className="h-3 w-3 rounded-full bg-amber-300" />
            <span className="h-3 w-3 rounded-full bg-emerald-300" />
          </div>
          <div className="mx-auto flex items-center gap-2 rounded-md bg-white px-3 py-1 text-xs text-slate-400 ring-1 ring-slate-200">
            <Icon name="shield" className="h-3 w-3" />
            app / answers / verified
          </div>
        </div>

        <div className="grid md:grid-cols-[180px_1fr]">
          {/* Mini sidebar */}
          <div className="hidden border-r border-slate-100 bg-slate-50/50 p-4 md:block">
            <div className="flex items-center gap-2">
              <LogoMark className="h-6 w-6" />
              <span className="text-xs font-semibold text-slate-700">Auditor</span>
            </div>
            <div className="mt-6 space-y-1.5">
              {['Overview', 'Audit runs', 'Verify answer', 'Review queue'].map((item, index) => (
                <div
                  key={item}
                  className={`rounded-md px-2.5 py-1.5 text-xs font-medium ${
                    index === 2 ? 'bg-indigo-50 text-indigo-700' : 'text-slate-500'
                  }`}
                >
                  {item}
                </div>
              ))}
            </div>
          </div>

          {/* Content */}
          <div className="grid gap-6 p-6 lg:grid-cols-5">
            <div className="lg:col-span-3">
              <div className="flex items-center justify-between">
                <p className="text-[11px] font-semibold tracking-wider text-slate-400 uppercase">
                  Assistant answer · market IN
                </p>
                <span className="animate-pop inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-medium text-emerald-700 ring-1 ring-emerald-200 [animation-delay:1.9s]">
                  <Icon name="check" className="h-3 w-3" />
                  Verified
                </span>
              </div>
              <div className="relative mt-3 overflow-hidden rounded-xl border border-slate-100 bg-slate-50/60 p-4">
                <HighlightedAnswer text={SAMPLE_TEXT} claims={SAMPLE_CLAIMS} />
                {/* A soft beam sweeping across the text: the agent "reading" the answer. */}
                <div
                  className="animate-scan pointer-events-none absolute inset-y-0 left-0 w-1/4 bg-gradient-to-r from-transparent via-indigo-400/20 to-transparent"
                  aria-hidden
                />
              </div>
            </div>
            <div className="space-y-2.5 lg:col-span-2">
              <p className="text-[11px] font-semibold tracking-wider text-slate-400 uppercase">Claims</p>
              {SAMPLE_CLAIMS.map((claim, index) => (
                <div
                  key={claim.id}
                  style={{ animationDelay: `${900 + index * 180}ms` }}
                  className="animate-fade-up flex items-start justify-between gap-3 rounded-lg border border-slate-100 bg-white px-3 py-2.5 shadow-sm transition-colors hover:border-indigo-200"
                >
                  <p className="text-xs leading-5 text-slate-600">{claim.rationale}</p>
                  <LabelBadge label={claim.label} />
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Floating card: agent trace. The outer element positions it, the inner one floats,
          so the two animations (position vs. bobbing) never fight over `transform`. */}
      <div className="absolute -top-10 -right-4 hidden w-64 xl:block">
        <div className="animate-float rounded-xl bg-white/95 p-4 shadow-float ring-1 ring-slate-900/5 backdrop-blur">
          <p className="flex items-center gap-2 text-xs font-semibold text-slate-900">
            <Icon name="tool" className="h-4 w-4 text-indigo-600" />
            Agent trace
            <span className="ml-auto flex h-2 w-2">
              <span className="absolute inline-flex h-2 w-2 animate-ping rounded-full bg-emerald-400 opacity-60" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
            </span>
          </p>
          <ol className="mt-3 space-y-2">
            {TRACE_STEPS.map((step, index) => (
              <li key={step} className="flex items-center gap-2">
                <span
                  style={{ animationDelay: `${1000 + index * 350}ms` }}
                  className="animate-pop flex h-4 w-4 items-center justify-center rounded-full bg-emerald-100 text-emerald-600"
                >
                  <Icon name="check" className="h-3 w-3" />
                </span>
                <code className="text-xs text-slate-600">{step}</code>
              </li>
            ))}
          </ol>
        </div>
      </div>

      {/* Floating card: human review */}
      <div className="absolute -bottom-10 -left-6 hidden w-72 xl:block">
        <div className="animate-float-slow rounded-xl bg-white/95 p-4 shadow-float ring-1 ring-slate-900/5 backdrop-blur [animation-delay:-3s]">
          <div className="flex items-start gap-3">
            <div className="flex h-9 w-9 flex-none items-center justify-center rounded-lg bg-rose-50 text-rose-600">
              <Icon name="users" className="h-5 w-5" />
            </div>
            <div>
              <p className="text-xs font-semibold text-slate-900">Sent to human review</p>
              <p className="mt-0.5 text-xs leading-5 text-slate-500">
                A contradicted price claim is waiting for a reviewer to confirm or dismiss it.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function LandingPage() {
  return (
    <>
      {/* Hero */}
      <section className="relative isolate overflow-hidden pt-16 pb-28 sm:pt-24">
        {/* Background: a faint grid and three slowly drifting colour glows ("aurora"). */}
        <div className="bg-grid fade-edges absolute inset-0 -z-10" />
        <div className="pointer-events-none absolute inset-0 -z-10 overflow-hidden" aria-hidden>
          <div className="animate-aurora absolute -top-40 left-[8%] h-[30rem] w-[30rem] rounded-full bg-indigo-300/35 blur-3xl" />
          <div className="animate-aurora absolute -top-24 right-[6%] h-[26rem] w-[26rem] rounded-full bg-violet-300/35 blur-3xl [animation-delay:-6s]" />
          <div className="animate-aurora absolute top-72 left-1/3 h-[24rem] w-[24rem] rounded-full bg-sky-200/45 blur-3xl [animation-delay:-11s]" />
        </div>

        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-3xl text-center">
            <a
              href="#how-it-works"
              className="animate-fade-up inline-flex items-center gap-2 rounded-full bg-white/80 py-1 pr-3 pl-1 text-sm text-slate-600 shadow-sm ring-1 ring-slate-200 backdrop-blur transition-shadow hover:shadow-md hover:ring-indigo-300"
            >
              <span className="rounded-full bg-indigo-600 px-2 py-0.5 text-xs font-semibold text-white">
                v0.1
              </span>
              Brand visibility and accuracy for AI search
              <Icon name="arrowRight" className="h-3.5 w-3.5 text-slate-400" />
            </a>
            <h1 className="animate-fade-up mt-8 text-4xl font-extrabold tracking-tight text-balance text-slate-900 [animation-delay:100ms] sm:text-6xl">
              Know what AI assistants say about{' '}
              <span className="text-shimmer animate-shimmer">your brand</span>
            </h1>
            <p className="animate-fade-up mx-auto mt-6 max-w-2xl text-lg leading-8 text-pretty text-slate-600 [animation-delay:200ms]">
              Measure how often assistants recommend you, and check every product claim they
              make against your own fact catalogue — with a human in the loop for anything that
              looks wrong.
            </p>
            <div className="animate-fade-up mt-10 flex flex-wrap justify-center gap-3 [animation-delay:300ms]">
              <ButtonLink
                to={PATHS.connect}
                size="lg"
                className="group shadow-lg shadow-indigo-600/25 hover:shadow-xl hover:shadow-indigo-600/30"
              >
                Connect API key
                <Icon name="arrowRight" className="h-4 w-4 transition-transform group-hover:translate-x-1" />
              </ButtonLink>
              <a href="#how-it-works" className={buttonClasses('secondary', 'lg')}>
                See how it works
              </a>
            </div>
            <div className="animate-fade-up mt-10 flex flex-wrap items-center justify-center gap-x-8 gap-y-3 text-sm text-slate-500 [animation-delay:400ms]">
              <span className="font-medium text-slate-400">Audits answers from</span>
              <span className="inline-flex items-center gap-2 font-semibold text-slate-700">
                <Icon name="sparkles" className="h-4 w-4 text-sky-500" />
                Google Gemini
              </span>
              <span className="inline-flex items-center gap-2 font-semibold text-slate-700">
                <Icon name="sparkles" className="h-4 w-4 text-emerald-500" />
                OpenAI
              </span>
            </div>
          </div>

          <div className="animate-fade-up [animation-delay:550ms]">
            <ProductIllustration />
          </div>
          <p className="animate-fade-in mt-16 text-center text-xs text-slate-400 [animation-delay:1.2s]">
            Illustration using a fictional demo brand. Not a real result.
          </p>
        </div>
      </section>

      {/* Features (bento grid) */}
      <section id="features" className="scroll-mt-20 border-t border-slate-100 bg-slate-50/60 py-24">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <SectionIntro
            eyebrow="What it does"
            title="Visibility and accuracy, measured honestly"
            text="Two questions every brand now asks: are AI assistants recommending us — and is what they say about us true?"
          />

          <div className="mt-14 grid gap-6 lg:grid-cols-3">
            {/* Verification agent (wide) */}
            <div className="rounded-3xl border border-slate-200/80 bg-white p-8 shadow-card lg:col-span-2">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-500 text-white shadow-sm">
                <Icon name="verify" className="h-6 w-6" />
              </div>
              <h3 className="mt-6 text-xl font-semibold text-slate-900">Claim verification agent</h3>
              <p className="mt-2 max-w-xl text-[15px] leading-7 text-slate-600">
                A tool-calling agent extracts every product claim, looks up the brand fact
                catalogue, and labels each claim supported, contradicted or unknown — citing the
                exact facts it read. It may only cite facts a tool returned in that conversation.
              </p>
              <div className="mt-8 flex flex-wrap items-center gap-2">
                {TRACE_STEPS.map((step, index) => (
                  <div key={step} className="flex items-center gap-2">
                    <code className="rounded-lg bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-700 ring-1 ring-slate-200">
                      {step}
                    </code>
                    {index < TRACE_STEPS.length - 1 ? (
                      <Icon name="arrowRight" className="h-4 w-4 text-slate-300" />
                    ) : null}
                  </div>
                ))}
              </div>
            </div>

            {/* Inclusion */}
            <div className="rounded-3xl border border-slate-200/80 bg-white p-8 shadow-card">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-sky-500 to-indigo-500 text-white shadow-sm">
                <Icon name="chart" className="h-6 w-6" />
              </div>
              <h3 className="mt-6 text-xl font-semibold text-slate-900">Inclusion you can trust</h3>
              <p className="mt-2 text-[15px] leading-7 text-slate-600">
                The same prompts are asked again and again. Each brand gets a rate with a 95%
                Wilson confidence interval — not one lucky answer.
              </p>
              <div className="mt-6 rounded-xl bg-slate-50 p-4 ring-1 ring-slate-100">
                <p className="mb-3 text-[11px] font-semibold tracking-wider text-slate-400 uppercase">
                  Rate and interval
                </p>
                {/* A picture of the idea only: no values, so nothing here reads as a result. */}
                <div className="relative h-2 w-full rounded-full bg-slate-200" aria-hidden>
                  <div className="absolute inset-y-0 left-[30%] w-[40%] rounded-full bg-indigo-200" />
                  <div className="absolute top-1/2 left-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white bg-indigo-600 shadow" />
                </div>
                <div className="mt-2 flex justify-between text-[11px] text-slate-400">
                  <span>observed rate (dot)</span>
                  <span>likely range (band)</span>
                </div>
                <p className="mt-3 text-xs text-slate-500">A wide band means few answers and more uncertainty.</p>
              </div>
            </div>

            {/* Human review */}
            <div className="rounded-3xl border border-slate-200/80 bg-white p-8 shadow-card">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-rose-500 to-pink-500 text-white shadow-sm">
                <Icon name="users" className="h-6 w-6" />
              </div>
              <h3 className="mt-6 text-xl font-semibold text-slate-900">Human review built in</h3>
              <p className="mt-2 text-[15px] leading-7 text-slate-600">
                Every contradicted claim lands in a review queue. A person confirms or dismisses
                it once, so no accusation reaches a client unchecked.
              </p>
            </div>

            {/* Typed failures (wide) */}
            <div className="rounded-3xl border border-slate-200/80 bg-white p-8 shadow-card lg:col-span-2">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-amber-400 to-orange-500 text-white shadow-sm">
                <Icon name="alert" className="h-6 w-6" />
              </div>
              <h3 className="mt-6 text-xl font-semibold text-slate-900">Every failure has a type</h3>
              <p className="mt-2 max-w-xl text-[15px] leading-7 text-slate-600">
                Agents fail in many ways. Each failure is classified, counted and stored with the
                full conversation, so you know whether to fix the prompt, a tool, the data, the
                configuration or the code.
              </p>
              <div className="mt-8 flex flex-wrap gap-2">
                {FAILURE_TYPES.map((type) => (
                  <span
                    key={type.name}
                    className={`rounded-full px-3 py-1 font-mono text-xs font-medium ring-1 ring-inset ${type.tone}`}
                  >
                    {type.name}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section id="how-it-works" className="scroll-mt-20 py-24">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <SectionIntro eyebrow="How it works" title="From prompt to reviewed report in four steps" center />
          <ol className="relative mt-16 grid gap-10 md:grid-cols-2 lg:grid-cols-4 lg:gap-6">
            <div className="absolute top-7 right-[12%] left-[12%] hidden h-px bg-gradient-to-r from-indigo-200 via-violet-200 to-indigo-200 lg:block" />
            {STEPS.map((step, index) => (
              <li key={step.title} className="relative text-center">
                <div className="relative mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-white text-indigo-600 shadow-card ring-1 ring-slate-200">
                  <Icon name={step.icon} className="h-6 w-6" />
                  <span className="absolute -top-2 -right-2 flex h-6 w-6 items-center justify-center rounded-full bg-indigo-600 text-xs font-bold text-white ring-4 ring-white">
                    {index + 1}
                  </span>
                </div>
                <h3 className="mt-6 text-base font-semibold text-slate-900">{step.title}</h3>
                <p className="mt-2 text-sm leading-6 text-slate-600">{step.text}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* API */}
      <section id="api" className="scroll-mt-20 border-y border-slate-100 bg-slate-50/60 py-24">
        <div className="mx-auto grid max-w-7xl items-center gap-12 px-4 sm:px-6 lg:grid-cols-2 lg:px-8">
          <div>
            <SectionIntro
              eyebrow="API-first"
              title="Everything in the app is one REST call away"
              text="Queue runs from your own pipelines, poll their status, read answers and work the review queue. Bearer keys, one error shape, and Idempotency-Key on every run."
            />
            <ul className="mt-8 space-y-3 text-sm text-slate-600">
              {[
                '202 Accepted + Location for queued runs',
                'Same key and body replays the same run — never a second, paid one',
                'Another client’s IDs answer 404, never 403',
              ].map((point) => (
                <li key={point} className="flex items-start gap-3">
                  <span className="mt-0.5 flex h-5 w-5 flex-none items-center justify-center rounded-full bg-indigo-100 text-indigo-700">
                    <Icon name="check" className="h-3.5 w-3.5" />
                  </span>
                  {point}
                </li>
              ))}
            </ul>
          </div>
          <div className="overflow-hidden rounded-2xl bg-white shadow-float ring-1 ring-slate-900/10">
            <div className="flex items-center justify-between border-b border-slate-100 bg-slate-50 px-4 py-2.5">
              <span className="flex items-center gap-2 text-xs font-medium text-slate-500">
                <Icon name="code" className="h-4 w-4" />
                Queue an audit run
              </span>
              <span className="rounded bg-indigo-50 px-2 py-0.5 font-mono text-[11px] font-semibold text-indigo-700">
                POST
              </span>
            </div>
            <pre className="overflow-x-auto p-5 font-mono text-[13px] leading-6 text-slate-700">
              <span className="text-violet-600">curl</span> -X POST /v1/audit-runs \{'\n'}
              {'  '}-H <span className="text-emerald-700">"Authorization: Bearer $KEY"</span> \{'\n'}
              {'  '}-H <span className="text-emerald-700">"Idempotency-Key: weekly-earbuds"</span> \{'\n'}
              {'  '}-d <span className="text-emerald-700">{"'{\"category\": \"earbuds\","}</span>{'\n'}
              {'       '}<span className="text-emerald-700">{"\"answer_providers\": [\"gemini\", \"openai\"],"}</span>{'\n'}
              {'       '}<span className="text-emerald-700">{"\"repeats\": 3}'"}</span>
            </pre>
          </div>
        </div>
      </section>

      {/* Reliability */}
      <section id="reliability" className="scroll-mt-20 py-24">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <SectionIntro
            eyebrow="Engineering"
            title="Built for reliable, repeatable runs"
            text="The parts that usually break in agent systems are designed in from the start."
          />
          <div className="mt-14 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {RELIABILITY.map((item) => (
              <div
                key={item.title}
                className="group rounded-2xl border border-slate-200/80 bg-white p-6 shadow-card transition-all hover:-translate-y-0.5 hover:shadow-md"
              >
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600 transition-colors group-hover:bg-indigo-600 group-hover:text-white">
                  <Icon name={item.icon} />
                </div>
                <h3 className="mt-5 font-semibold text-slate-900">{item.title}</h3>
                <p className="mt-2 text-sm leading-6 text-slate-600">{item.text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Call to action */}
      <section className="px-4 pb-24 sm:px-6 lg:px-8">
        <div className="relative isolate mx-auto max-w-7xl overflow-hidden rounded-3xl bg-gradient-to-br from-indigo-600 via-indigo-600 to-violet-600 px-6 py-16 text-center shadow-float sm:px-12">
          <div className="bg-grid absolute inset-0 -z-10 opacity-20 invert" />
          <div className="absolute -top-24 -right-24 -z-10 h-72 w-72 rounded-full bg-violet-400/40 blur-3xl" />
          <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
            Start your first audit
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-lg text-indigo-100">
            Connect with an API key from your administrator, created with{' '}
            <code className="rounded bg-white/15 px-1.5 py-0.5 text-base">auditor create-api-key</code>.
          </p>
          <div className="mt-10 flex flex-wrap justify-center gap-3">
            <ButtonLink to={PATHS.connect} size="lg" variant="white">
              Connect API key
              <Icon name="arrowRight" className="h-4 w-4" />
            </ButtonLink>
            <a href="#features" className={buttonClasses('glass', 'lg')}>
              Explore features
            </a>
          </div>
        </div>
      </section>
    </>
  )
}
