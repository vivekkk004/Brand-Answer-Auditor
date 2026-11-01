import HighlightedAnswer from '../components/domain/HighlightedAnswer'
import { LabelBadge } from '../components/domain/StatusBadges'
import { ButtonLink } from '../components/ui/Button'
import { buttonClasses } from '../components/ui/buttonStyles'
import Icon from '../components/ui/Icon'
import { PATHS } from '../routes/paths'

// An ILLUSTRATION built from the real components, using the fictional demo catalogue
// (data/demo). It is labelled as such and contains no metrics or results.
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

const FEATURES = [
  {
    icon: 'chart',
    title: 'Inclusion you can trust',
    text: 'AI answers change every time. The same shopping prompts are asked again and again, and each brand gets a rate with a 95% Wilson confidence interval — not a lucky single answer.',
  },
  {
    icon: 'verify',
    title: 'Claim verification agent',
    text: 'A tool-calling agent extracts every product claim, looks up the brand fact catalogue and labels it supported, contradicted or unknown — citing the exact facts it read.',
  },
  {
    icon: 'users',
    title: 'Human review built in',
    text: 'Every contradicted claim lands in a review queue. A person confirms or dismisses it once, so no accusation reaches a client unchecked.',
  },
]

const STEPS = [
  {
    title: 'Queue an audit run',
    text: 'Pick a category, the assistants to ask and how many repeats. The request is idempotent, so a retry never starts a second run.',
  },
  {
    title: 'Collect answers',
    text: 'A background worker asks every prompt on Gemini and OpenAI, and finds brand mentions with plain, deterministic code.',
  },
  {
    title: 'Verify every claim',
    text: 'The agent quotes each claim exactly; code computes its position and checks every citation against the catalogue.',
  },
  {
    title: 'Review and report',
    text: 'Contradictions go to reviewers; the run report shows inclusion, label shares, failures, tokens and cost.',
  },
]

const RELIABILITY = [
  { icon: 'refresh', title: 'Retries done right', text: 'Only rate limits, server errors and timeouts are retried, with exponential backoff and jitter.' },
  { icon: 'shield', title: 'Hard budgets', text: 'Every run has a model-call budget. Verification reserves its worst case first, so a run never overspends.' },
  { icon: 'bolt', title: 'Resumable worker', text: 'Answers are saved one by one. A crashed run is picked up again and never pays for an answer twice.' },
  { icon: 'check', title: 'Strict validation', text: 'Quotes must match the text exactly and facts must have been looked up. Invalid output is never saved.' },
  { icon: 'key', title: 'Isolated clients', text: 'API keys are stored only as hashes, and one client can never see another client’s data.' },
  { icon: 'runs', title: 'Full trace', text: 'Each answer keeps the agent’s whole conversation — every tool call and result — for debugging.' },
]

export default function LandingPage() {
  return (
    <>
      {/* Hero */}
      <section className="relative overflow-hidden bg-gradient-to-b from-indigo-50/70 via-white to-white">
        <div className="mx-auto grid max-w-7xl items-center gap-12 px-4 py-16 sm:px-6 lg:grid-cols-2 lg:px-8 lg:py-24">
          <div>
            <span className="inline-flex items-center gap-2 rounded-full border border-indigo-200 bg-white px-3 py-1 text-xs font-medium text-indigo-700">
              <span className="h-1.5 w-1.5 rounded-full bg-indigo-500" />
              AI answer auditing for brands
            </span>
            <h1 className="mt-6 text-4xl font-semibold tracking-tight text-slate-900 sm:text-5xl">
              Know what AI assistants say about your brand
            </h1>
            <p className="mt-6 max-w-xl text-lg leading-8 text-slate-600">
              Measure how often assistants recommend you, and check every product claim they
              make against your own fact catalogue — with a human in the loop for anything
              that looks wrong.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <ButtonLink to={PATHS.connect} size="lg">
                Connect API key
                <Icon name="arrowRight" className="h-4 w-4" />
              </ButtonLink>
              <a href="#how-it-works" className={buttonClasses('secondary', 'lg')}>
                See how it works
              </a>
            </div>
            <ul className="mt-10 space-y-3 text-sm text-slate-600">
              {[
                'Repeated prompts, reported with confidence intervals',
                'Every decisive label cites a catalogue fact',
                'Contradictions are confirmed by a person',
              ].map((point) => (
                <li key={point} className="flex items-center gap-3">
                  <span className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-100 text-emerald-700">
                    <Icon name="check" className="h-3.5 w-3.5" />
                  </span>
                  {point}
                </li>
              ))}
            </ul>
          </div>

          {/* Product illustration */}
          <div className="relative">
            <div className="absolute -inset-4 -z-10 rounded-3xl bg-gradient-to-tr from-indigo-100 to-sky-50 blur-2xl" />
            <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl shadow-slate-200/60">
              <div className="flex items-center gap-2 border-b border-slate-100 bg-slate-50 px-4 py-3">
                <span className="h-2.5 w-2.5 rounded-full bg-slate-300" />
                <span className="h-2.5 w-2.5 rounded-full bg-slate-300" />
                <span className="h-2.5 w-2.5 rounded-full bg-slate-300" />
                <span className="ml-3 text-xs font-medium text-slate-500">Verified answer</span>
              </div>
              <div className="p-6">
                <p className="text-xs font-medium tracking-wide text-slate-400 uppercase">
                  Assistant answer · market IN
                </p>
                <div className="mt-3">
                  <HighlightedAnswer text={SAMPLE_TEXT} claims={SAMPLE_CLAIMS} />
                </div>
                <div className="mt-6 space-y-2.5">
                  {SAMPLE_CLAIMS.map((claim) => (
                    <div
                      key={claim.id}
                      className="flex items-start justify-between gap-4 rounded-lg border border-slate-100 px-3 py-2.5"
                    >
                      <p className="text-sm text-slate-700">{claim.rationale}</p>
                      <LabelBadge label={claim.label} />
                    </div>
                  ))}
                </div>
                <p className="mt-5 text-xs text-slate-400">
                  Illustration using a fictional demo brand. Not a real result.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="scroll-mt-20 py-20">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="max-w-2xl">
            <p className="text-sm font-semibold text-indigo-600">What it does</p>
            <h2 className="mt-2 text-3xl font-semibold tracking-tight text-slate-900">
              Visibility and accuracy, measured honestly
            </h2>
            <p className="mt-4 text-slate-600">
              Two questions every brand now asks: are AI assistants recommending us, and is
              what they say about us true?
            </p>
          </div>
          <div className="mt-12 grid gap-6 md:grid-cols-3">
            {FEATURES.map((feature) => (
              <div
                key={feature.title}
                className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition-shadow hover:shadow-md"
              >
                <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600">
                  <Icon name={feature.icon} className="h-6 w-6" />
                </div>
                <h3 className="mt-5 text-lg font-semibold text-slate-900">{feature.title}</h3>
                <p className="mt-2 text-sm leading-6 text-slate-600">{feature.text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section id="how-it-works" className="scroll-mt-20 border-y border-slate-200 bg-slate-50 py-20">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="max-w-2xl">
            <p className="text-sm font-semibold text-indigo-600">How it works</p>
            <h2 className="mt-2 text-3xl font-semibold tracking-tight text-slate-900">
              From prompt to reviewed report in four steps
            </h2>
          </div>
          <ol className="mt-12 grid gap-6 md:grid-cols-2 lg:grid-cols-4">
            {STEPS.map((step, index) => (
              <li key={step.title} className="relative rounded-2xl border border-slate-200 bg-white p-6">
                <span className="flex h-9 w-9 items-center justify-center rounded-full bg-indigo-600 text-sm font-semibold text-white">
                  {index + 1}
                </span>
                <h3 className="mt-4 font-semibold text-slate-900">{step.title}</h3>
                <p className="mt-2 text-sm leading-6 text-slate-600">{step.text}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* Reliability */}
      <section id="reliability" className="scroll-mt-20 py-20">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="max-w-2xl">
            <p className="text-sm font-semibold text-indigo-600">Engineering</p>
            <h2 className="mt-2 text-3xl font-semibold tracking-tight text-slate-900">
              Built for reliable, repeatable runs
            </h2>
            <p className="mt-4 text-slate-600">
              Agents fail in many ways. Each failure is typed — provider, prompt, tool, data,
              config or code — so it can be counted and fixed.
            </p>
          </div>
          <div className="mt-12 grid gap-x-8 gap-y-10 sm:grid-cols-2 lg:grid-cols-3">
            {RELIABILITY.map((item) => (
              <div key={item.title} className="flex gap-4">
                <div className="flex h-10 w-10 flex-none items-center justify-center rounded-lg bg-slate-100 text-slate-700">
                  <Icon name={item.icon} />
                </div>
                <div>
                  <h3 className="font-semibold text-slate-900">{item.title}</h3>
                  <p className="mt-1 text-sm leading-6 text-slate-600">{item.text}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Call to action */}
      <section className="px-4 pb-20 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl rounded-3xl bg-indigo-600 px-6 py-14 text-center sm:px-12">
          <h2 className="text-3xl font-semibold tracking-tight text-white">Start your first audit</h2>
          <p className="mx-auto mt-3 max-w-xl text-indigo-100">
            Connect with an API key from your administrator (created with{' '}
            <code className="rounded bg-indigo-500/60 px-1.5 py-0.5 text-sm">auditor create-api-key</code>
            ).
          </p>
          <div className="mt-8">
            <ButtonLink to={PATHS.connect} size="lg" variant="secondary">
              Connect API key
            </ButtonLink>
          </div>
        </div>
      </section>
    </>
  )
}
