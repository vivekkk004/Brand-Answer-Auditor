import { useEffect, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { useNavigate } from 'react-router-dom'
import { Button } from '../components/ui/Button'
import Card from '../components/ui/Card'
import DescriptionList from '../components/ui/DescriptionList'
import ErrorBanner from '../components/ui/ErrorBanner'
import Field from '../components/ui/Field'
import Icon from '../components/ui/Icon'
import { INPUT_CLASSES } from '../components/ui/inputStyles'
import PageHeader from '../components/ui/PageHeader'
import {
  INITIAL_RUN_VALUES,
  serverFieldErrors,
  toRunConfig,
  validateRunForm,
} from '../features/runs/runForm'
import { createRun, resetCreate } from '../features/runs/runsSlice'
import { PATHS, runPath } from '../routes/paths'
import { PROMPT_VERSIONS, PROVIDERS } from '../utils/constants'
import { newIdempotencyKey } from '../utils/idempotency'

export default function NewRunPage() {
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const create = useSelector((state) => state.runs.create)
  const [values, setValues] = useState(INITIAL_RUN_VALUES)
  const [touched, setTouched] = useState(false)
  // One key per set of form values: re-submitting the same values replays the same run.
  const [idempotencyKey, setIdempotencyKey] = useState(newIdempotencyKey)

  useEffect(() => {
    dispatch(resetCreate())
    return () => dispatch(resetCreate())
  }, [dispatch])

  const clientErrors = validateRunForm(values)
  const serverErrors = serverFieldErrors(create.error)
  const errors = touched ? { ...serverErrors, ...clientErrors } : serverErrors
  const otherServerError =
    create.error && !Object.keys(serverErrors).length ? create.error : null

  function update(field, value) {
    setValues((current) => ({ ...current, [field]: value }))
    // Different values are a different request, so they need a new key.
    setIdempotencyKey(newIdempotencyKey())
    if (create.error) dispatch(resetCreate())
  }

  function toggleProvider(provider) {
    update(
      'providers',
      values.providers.includes(provider)
        ? values.providers.filter((value) => value !== provider)
        : [...values.providers, provider],
    )
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setTouched(true)
    if (Object.keys(clientErrors).length) return
    const result = await dispatch(createRun({ config: toRunConfig(values), idempotencyKey }))
    if (createRun.fulfilled.match(result)) {
      navigate(runPath(result.payload.run.id), { state: { replayed: result.payload.replayed } })
    }
  }

  return (
    <>
      <PageHeader
        title="New audit run"
        description="Ask AI assistants your category prompts, then verify every answer."
        back={{ to: PATHS.runs, label: 'Audit runs' }}
      />

      <form onSubmit={handleSubmit} noValidate className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Card
            title="What to ask"
            description="Prompts are chosen by category from the catalogue."
            icon={<Icon name="search" className="h-5 w-5" />}
          >
            <div className="grid gap-5 sm:grid-cols-2">
              <Field id="category" label="Category" error={errors.category} hint="The demo data has “earbuds”.">
                <input
                  id="category"
                  className={INPUT_CLASSES}
                  value={values.category}
                  onChange={(event) => update('category', event.target.value.trim())}
                  aria-invalid={Boolean(errors.category) || undefined}
                />
              </Field>
              <Field
                id="prompt-ids"
                label="Prompt IDs (optional)"
                error={errors.prompt_ids}
                hint="Comma separated, for example p01, p02. Empty means all prompts in the category."
              >
                <input
                  id="prompt-ids"
                  className={INPUT_CLASSES}
                  value={values.promptIds}
                  placeholder="p01, p02"
                  onChange={(event) => update('promptIds', event.target.value)}
                  aria-invalid={Boolean(errors.prompt_ids) || undefined}
                />
              </Field>
            </div>
          </Card>

          <Card
            title="Who to ask"
            description="One or two assistants. Each is asked every prompt."
            icon={<Icon name="users" className="h-5 w-5" />}
          >
            <fieldset>
              <legend className="sr-only">Assistants</legend>
              <div className="grid gap-3 sm:grid-cols-2">
                {PROVIDERS.map((provider) => {
                  const checked = values.providers.includes(provider.value)
                  return (
                    <label
                      key={provider.value}
                      className={`flex cursor-pointer items-center gap-3 rounded-xl border p-4 transition-all duration-150 focus-within:ring-4 focus-within:ring-indigo-500/15 ${
                        checked
                          ? 'border-indigo-400 bg-indigo-50/60 shadow-sm'
                          : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'
                      }`}
                    >
                      <input
                        type="checkbox"
                        className="h-4 w-4 accent-indigo-600"
                        checked={checked}
                        onChange={() => toggleProvider(provider.value)}
                      />
                      <span className="flex-1 text-sm font-medium text-slate-800">{provider.label}</span>
                      <Icon
                        name="sparkles"
                        className={`h-4 w-4 transition-colors ${checked ? 'text-indigo-500' : 'text-slate-300'}`}
                      />
                    </label>
                  )
                })}
              </div>
              {errors.answer_providers ? (
                <p className="mt-2 flex items-center gap-1.5 text-sm text-rose-600">
                  <span className="h-1 w-1 flex-none rounded-full bg-rose-500" aria-hidden />
                  {errors.answer_providers}
                </p>
              ) : null}
            </fieldset>
          </Card>

          <Card
            title="How to check"
            description="Repeats measure how stable answers are."
            icon={<Icon name="verify" className="h-5 w-5" />}
          >
            <div className="grid gap-5 sm:grid-cols-3">
              <Field id="repeats" label="Repeats" error={errors.repeats} hint="1 to 5 per prompt.">
                <input
                  id="repeats"
                  type="number"
                  min={1}
                  max={5}
                  className={INPUT_CLASSES}
                  value={values.repeats}
                  onChange={(event) => update('repeats', Number(event.target.value))}
                  aria-invalid={Boolean(errors.repeats) || undefined}
                />
              </Field>
              <Field id="agent-version" label="Agent prompt">
                <select
                  id="agent-version"
                  className={INPUT_CLASSES}
                  value={values.agentVersion}
                  onChange={(event) => update('agentVersion', event.target.value)}
                >
                  {PROMPT_VERSIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </Field>
              <Field
                id="max-calls"
                label="Model-call budget"
                error={errors.max_model_calls}
                hint="Hard cap; the run stops as “partial” when reached."
              >
                <input
                  id="max-calls"
                  type="number"
                  min={1}
                  max={5000}
                  className={INPUT_CLASSES}
                  value={values.maxModelCalls}
                  onChange={(event) => update('maxModelCalls', Number(event.target.value))}
                  aria-invalid={Boolean(errors.max_model_calls) || undefined}
                />
              </Field>
            </div>
          </Card>
        </div>

        {/* On large screens the summary stays in view while the form scrolls. */}
        <div className="space-y-6 lg:sticky lg:top-24 lg:self-start">
          <Card title="Summary" icon={<Icon name="chart" className="h-5 w-5" />}>
            <DescriptionList
              items={[
                [
                  'Answers per prompt',
                  `${values.providers.length} × ${values.repeats || 0} = ${values.providers.length * (values.repeats || 0)}`,
                ],
                ['Cost per answer', '1 call + up to 4 to verify'],
              ]}
            />
            <p className="mt-5 rounded-lg bg-slate-50 p-3 text-xs leading-5 text-slate-500 ring-1 ring-slate-100">
              The run is queued and processed by a worker in the background. Submitting the
              same values twice returns the same run.
            </p>
            {otherServerError ? (
              <div className="mt-4">
                <ErrorBanner error={otherServerError} title="Could not queue the run" />
              </div>
            ) : null}
            <Button type="submit" size="lg" className="mt-5 w-full" loading={create.status === 'loading'}>
              Queue run
            </Button>
          </Card>
        </div>
      </form>
    </>
  )
}
