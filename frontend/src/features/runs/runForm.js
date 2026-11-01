/**
 * The New run form's logic, kept out of the component so it can be tested on its own.
 * The limits are the same as RunConfig on the server (src/auditor/audit/run_config.py), so
 * most mistakes are caught before a request is sent; the server still checks everything.
 */

const ID_PATTERN = /^[a-z0-9][a-z0-9-]*$/

export const INITIAL_RUN_VALUES = {
  category: 'earbuds',
  promptIds: '',
  providers: ['gemini'],
  repeats: 3,
  agentVersion: 'v1',
  maxModelCalls: 500,
}

export function parsePromptIds(text) {
  const ids = text
    .split(',')
    .map((id) => id.trim())
    .filter(Boolean)
  return ids.length ? ids : null
}

/** Errors keyed by the API's field names, so client and server errors share one shape. */
export function validateRunForm(values) {
  const errors = {}
  if (!ID_PATTERN.test(values.category)) {
    errors.category = 'Use lowercase letters, digits and dashes, for example "earbuds".'
  }
  const promptIds = parsePromptIds(values.promptIds)
  if (promptIds && promptIds.some((id) => !ID_PATTERN.test(id))) {
    errors.prompt_ids = 'Prompt IDs look like "p01", separated by commas.'
  } else if (promptIds && new Set(promptIds).size !== promptIds.length) {
    errors.prompt_ids = 'Each prompt ID may appear once.'
  }
  if (values.providers.length < 1 || values.providers.length > 2) {
    errors.answer_providers = 'Choose one or two assistants.'
  }
  if (!Number.isInteger(values.repeats) || values.repeats < 1 || values.repeats > 5) {
    errors.repeats = 'Between 1 and 5.'
  }
  const calls = values.maxModelCalls
  if (!Number.isInteger(calls) || calls < 1 || calls > 5000) {
    errors.max_model_calls = 'Between 1 and 5,000.'
  }
  return errors
}

/** Form values -> the POST /v1/audit-runs body. */
export function toRunConfig(values) {
  return {
    category: values.category,
    prompt_ids: parsePromptIds(values.promptIds),
    answer_providers: values.providers,
    repeats: values.repeats,
    agent_version: values.agentVersion,
    max_model_calls: values.maxModelCalls,
  }
}

/** A 422 from the server -> per-field messages. Validation details carry loc ["body", field]. */
export function serverFieldErrors(error) {
  if (!error) return {}
  if (error.code === 'no_matching_prompts') return { category: error.message }
  const fields = {}
  for (const detail of error.details || []) {
    const field = detail.loc?.[0] === 'body' ? detail.loc[1] : null
    if (field && !fields[field]) fields[field] = detail.msg
  }
  return fields
}
