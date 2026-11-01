import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import {
  ANSWER_TEXT,
  apiError,
  jsonResponse,
  makeClaim,
  makeReviewItem,
  makeRun,
  TEST_KEY,
} from '../test/fixtures'
import { stubFetch } from '../test/fetchStub'
import { renderApp } from '../test/render'

// Every app page checks API health from the layout.
const HEALTH = { 'GET /healthz': () => jsonResponse(200, { status: 'ok' }) }

describe('routing', () => {
  it('sends a visitor without a key from /app to the connect page', async () => {
    stubFetch(HEALTH)
    renderApp('/app/runs')
    expect(await screen.findByRole('heading', { name: 'Connect your API key' })).toBeInTheDocument()
  })

  it('connects and returns to the page the visitor asked for', async () => {
    stubFetch({
      ...HEALTH,
      'GET /v1/review-items': () => jsonResponse(200, { items: [], limit: 1, offset: 0 }),
      'GET /v1/audit-runs': () => jsonResponse(200, { items: [], limit: 20, offset: 0 }),
    })
    const { router } = renderApp('/app/runs')

    await userEvent.type(await screen.findByLabelText('API key'), TEST_KEY)
    await userEvent.click(screen.getByRole('button', { name: 'Connect' }))

    await waitFor(() => expect(router.state.location.pathname).toBe('/app/runs'))
    expect(await screen.findByText('No audit runs yet')).toBeInTheDocument()
  })

  it('shows the landing page illustration as not a real result', () => {
    renderApp('/')
    expect(
      screen.getByRole('heading', { name: 'Know what AI assistants say about your brand' }),
    ).toBeInTheDocument()
    expect(screen.getByText(/Not a real result/)).toBeInTheDocument()
  })

  it('shows a 404 page for unknown URLs', () => {
    renderApp('/nope')
    expect(screen.getByRole('heading', { name: 'Page not found' })).toBeInTheDocument()
  })
})

describe('app pages', () => {
  it('lists runs from the API', async () => {
    stubFetch({
      ...HEALTH,
      'GET /v1/audit-runs': () => jsonResponse(200, { items: [makeRun()], limit: 20, offset: 0 }),
    })
    renderApp('/app/runs', { apiKey: TEST_KEY })

    expect(await screen.findByText('11111111')).toBeInTheDocument()
    const table = within(screen.getByRole('table'))
    expect(table.getByText('Queued')).toBeInTheDocument()
    expect(table.getByText('0 / 500')).toBeInTheDocument()
  })

  it('shows a server validation error next to its field', async () => {
    stubFetch({
      ...HEALTH,
      'POST /v1/audit-runs': () =>
        apiError(422, 'validation_error', 'the request is invalid', {
          details: [{ loc: ['body', 'category'], msg: 'no such category on the server' }],
        }),
    })
    renderApp('/app/runs/new', { apiKey: TEST_KEY })

    await userEvent.click(await screen.findByRole('button', { name: 'Queue run' }))

    expect(await screen.findByText('no such category on the server')).toBeInTheDocument()
  })

  it('opens the new run after queueing it, with the same key on a resubmit', async () => {
    const fetchMock = stubFetch({
      ...HEALTH,
      'POST /v1/audit-runs': () => jsonResponse(202, makeRun()),
      [`GET /v1/audit-runs/${makeRun().id}`]: () => jsonResponse(200, makeRun()),
    })
    const { router } = renderApp('/app/runs/new', { apiKey: TEST_KEY })

    await userEvent.click(await screen.findByRole('button', { name: 'Queue run' }))

    await waitFor(() => expect(router.state.location.pathname).toBe(`/app/runs/${makeRun().id}`))
    const post = fetchMock.mock.calls.find(([, init]) => init.method === 'POST')
    expect(post[1].headers['Idempotency-Key']).toMatch(/^ui-/)
    expect(await screen.findByText(/Metrics appear when the run finishes/)).toBeInTheDocument()
  })

  it('links a failed verification to its saved answer', async () => {
    stubFetch({
      ...HEALTH,
      'POST /v1/verify': () =>
        apiError(503, 'verifier_not_configured', 'no verifier provider given', { answer_id: 'a1' }),
    })
    renderApp('/app/verify', { apiKey: TEST_KEY })

    await userEvent.type(await screen.findByLabelText('Answer text'), 'The Zentro Air 2 costs ₹6,999.')
    await userEvent.click(screen.getByRole('button', { name: /Verify claims/ }))

    expect(await screen.findByText('no verifier provider given')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open the saved answer' })).toHaveAttribute(
      'href',
      '/app/answers/a1',
    )
  })

  it('highlights a verified answer’s claims and lists them (fixture data, not a real result)', async () => {
    const claim = makeClaim()
    const answer = {
      id: 'a1',
      run_id: null,
      prompt_id: null,
      provider: null,
      model: null,
      repeat_index: null,
      market: 'IN',
      text: ANSWER_TEXT,
      status: 'verified',
      error_type: null,
      error_message: null,
      brands_mentioned: ['zentro'],
      verifier_model: 'test-model',
      prompt_version: 'v1',
      verification_turns: 2,
      verification_latency_ms: 1234,
      timed_out: false,
      usage: { verification: { input: 100, output: 20, thinking: null } },
      claims: [claim],
      exchanges: [
        { role: 'user', content: 'check this', tool_calls: [], tool_call_id: null, tool_name: null },
        {
          role: 'assistant',
          content: '',
          tool_calls: [{ id: 'c1', name: 'get_brand_facts', arguments: { brand_id: 'zentro' } }],
          tool_call_id: null,
          tool_name: null,
        },
      ],
      created_at: '2026-01-01T12:00:00Z',
    }
    stubFetch({ ...HEALTH, 'GET /v1/answers/a1': () => jsonResponse(200, answer) })
    const { container } = renderApp('/app/answers/a1', { apiKey: TEST_KEY })

    await screen.findByText('Answer text')
    const marks = container.querySelectorAll('mark')
    expect([...marks].map((mark) => [mark.textContent, mark.dataset.label])).toEqual([
      [claim.quote, 'contradicted'],
    ])
    expect(screen.getByText('Test rationale.')).toBeInTheDocument()
    expect(screen.getByText('zentro-air2-price-in')).toBeInTheDocument()
    expect(screen.getByText('Show 2 step(s)')).toBeInTheDocument()
    expect(screen.getByText('get_brand_facts')).toBeInTheDocument()
  })

  it('does not claim "no claims found" for a failed answer', async () => {
    stubFetch({
      ...HEALTH,
      'GET /v1/answers/a2': () =>
        jsonResponse(200, {
          id: 'a2', run_id: null, prompt_id: null, provider: null, model: null, repeat_index: null,
          market: null, text: 'Some text.', status: 'verification_failed', error_type: 'config',
          error_message: 'no verifier provider given', brands_mentioned: [], verifier_model: null,
          prompt_version: null, verification_turns: null, verification_latency_ms: null,
          timed_out: false, usage: {}, claims: [], exchanges: null, created_at: '2026-01-01T12:00:00Z',
        }),
    })
    renderApp('/app/answers/a2', { apiKey: TEST_KEY })

    expect(await screen.findByText('Not verified')).toBeInTheDocument()
    expect(screen.queryByText('No checkable claims')).not.toBeInTheDocument()
  })

  it('shows "already decided" on a 409 and reloads the queue', async () => {
    const item = makeReviewItem()
    const fetchMock = stubFetch({
      ...HEALTH,
      'GET /v1/review-items': () => jsonResponse(200, { items: [item], limit: 20, offset: 0 }),
      [`PATCH /v1/review-items/${item.id}`]: () =>
        apiError(409, 'already_decided', 'this item was already dismissed'),
    })
    renderApp('/app/review', { apiKey: TEST_KEY })

    await userEvent.click(await screen.findByRole('button', { name: /Confirm — the claim is wrong/ }))

    expect(await screen.findByText('Already decided')).toBeInTheDocument()
    const listCalls = fetchMock.mock.calls.filter(([url]) => String(url).startsWith('/v1/review-items?'))
    expect(listCalls).toHaveLength(2)
  })
})
