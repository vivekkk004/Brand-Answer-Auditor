import { describe, expect, it } from 'vitest'
import { INITIAL_RUN_VALUES, serverFieldErrors, toRunConfig, validateRunForm } from './runForm'

describe('run form', () => {
  it('accepts the defaults', () => {
    expect(validateRunForm(INITIAL_RUN_VALUES)).toEqual({})
  })

  it('applies the same limits as RunConfig', () => {
    const errors = validateRunForm({
      ...INITIAL_RUN_VALUES,
      category: 'Ear Buds',
      promptIds: 'p01, p01',
      providers: [],
      repeats: 6,
      maxModelCalls: 5001,
    })
    expect(Object.keys(errors).sort()).toEqual([
      'answer_providers',
      'category',
      'max_model_calls',
      'prompt_ids',
      'repeats',
    ])
  })

  it('allows one to three assistants, Groq included', () => {
    const withProviders = (providers) => validateRunForm({ ...INITIAL_RUN_VALUES, providers })
    expect(withProviders(['groq'])).toEqual({})
    expect(withProviders(['gemini', 'openai', 'groq'])).toEqual({})
    expect(withProviders(['gemini', 'openai', 'groq', 'other'])).toHaveProperty('answer_providers')
    expect(toRunConfig({ ...INITIAL_RUN_VALUES, providers: ['gemini', 'groq'] }).answer_providers).toEqual([
      'gemini',
      'groq',
    ])
  })

  it('builds the request body with prompt IDs as a list, or null for all', () => {
    expect(toRunConfig({ ...INITIAL_RUN_VALUES, promptIds: ' p01, ,p02 ' }).prompt_ids).toEqual([
      'p01',
      'p02',
    ])
    expect(toRunConfig(INITIAL_RUN_VALUES)).toEqual({
      category: 'earbuds',
      prompt_ids: null,
      answer_providers: ['gemini'],
      repeats: 3,
      agent_version: 'v1',
      max_model_calls: 500,
    })
  })

  it('maps server errors to fields', () => {
    expect(
      serverFieldErrors({
        code: 'validation_error',
        details: [{ loc: ['body', 'repeats'], msg: 'Input should be less than or equal to 5' }],
      }),
    ).toEqual({ repeats: 'Input should be less than or equal to 5' })
    expect(
      serverFieldErrors({ code: 'no_matching_prompts', message: "no prompts in category 'x'" }),
    ).toEqual({ category: "no prompts in category 'x'" })
  })
})
