/**
 * Response shapes copied from the API's schemas (src/auditor/api/schemas.py).
 * Values are made up for tests only; they are not results.
 */
export const TEST_KEY = 'baa_test-key'

export const ANSWER_TEXT = 'The Zentro Air 2 costs ₹6,999 in India, and it sounds great.'

export function makeRun(overrides = {}) {
  return {
    id: '11111111-1111-1111-1111-111111111111',
    status: 'queued',
    config: {
      category: 'earbuds',
      prompt_ids: null,
      answer_providers: ['gemini'],
      repeats: 3,
      agent_version: 'v1',
      max_model_calls: 500,
    },
    model_calls: 0,
    max_model_calls: 500,
    metrics: null,
    failure_reason: null,
    created_at: '2026-01-01T12:00:00Z',
    started_at: null,
    finished_at: null,
    ...overrides,
  }
}

export function makeClaim(overrides = {}) {
  const quote = 'The Zentro Air 2 costs ₹6,999'
  return {
    id: '22222222-2222-2222-2222-222222222222',
    quote,
    start: 0,
    end: quote.length,
    brand_id: 'zentro',
    product: 'Zentro Air 2',
    attribute: 'price',
    label: 'contradicted',
    fact_ids: ['zentro-air2-price-in'],
    rationale: 'Test rationale.',
    ...overrides,
  }
}

export function makeReviewItem(overrides = {}) {
  return {
    id: '33333333-3333-3333-3333-333333333333',
    status: 'open',
    note: null,
    created_at: '2026-01-01T12:00:00Z',
    resolved_at: null,
    answer_id: '44444444-4444-4444-4444-444444444444',
    claim: makeClaim(),
    ...overrides,
  }
}

/** A fetch Response with a JSON body. */
export function jsonResponse(status, body, headers = {}) {
  return new Response(body === undefined ? '' : JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json', ...headers },
  })
}

export function apiError(status, code, message, extra = {}) {
  return jsonResponse(status, { error: { code, message, ...extra } })
}
