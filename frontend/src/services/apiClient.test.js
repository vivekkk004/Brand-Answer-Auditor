import { describe, expect, it, vi } from 'vitest'
import { apiError, jsonResponse } from '../test/fixtures'
import { apiRequest, apiRequestFull, ApiError, setApiKeyProvider, toErrorPayload } from './apiClient'

describe('apiClient', () => {
  it('sends the stored key as a Bearer token and leaves empty query values out', async () => {
    setApiKeyProvider(() => 'baa_stored')
    const fetchMock = vi.fn(async () => jsonResponse(200, { items: [] }))
    vi.stubGlobal('fetch', fetchMock)

    const data = await apiRequest('/v1/audit-runs', { query: { status: '', limit: 20, offset: 0 } })

    expect(data).toEqual({ items: [] })
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/v1/audit-runs?limit=20&offset=0')
    expect(init.headers.Authorization).toBe('Bearer baa_stored')
  })

  it('uses an explicit key over the stored one, and sends none when auth is off', async () => {
    setApiKeyProvider(() => 'baa_stored')
    const fetchMock = vi.fn(async () => jsonResponse(200, {}))
    vi.stubGlobal('fetch', fetchMock)

    await apiRequest('/v1/review-items', { apiKey: 'baa_explicit' })
    await apiRequest('/healthz', { auth: false })

    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBe('Bearer baa_explicit')
    expect(fetchMock.mock.calls[1][1].headers.Authorization).toBeUndefined()
  })

  it('sends JSON bodies and the Idempotency-Key header, and exposes response headers', async () => {
    const fetchMock = vi.fn(async () =>
      jsonResponse(200, { id: 'r1' }, { 'Idempotent-Replayed': 'true' }),
    )
    vi.stubGlobal('fetch', fetchMock)

    const { data, status, headers } = await apiRequestFull('/v1/audit-runs', {
      method: 'POST',
      body: { category: 'earbuds' },
      idempotencyKey: 'key-1',
    })

    const init = fetchMock.mock.calls[0][1]
    expect(init.body).toBe('{"category":"earbuds"}')
    expect(init.headers['Content-Type']).toBe('application/json')
    expect(init.headers['Idempotency-Key']).toBe('key-1')
    expect([data, status, headers.get('Idempotent-Replayed')]).toEqual([{ id: 'r1' }, 200, 'true'])
  })

  it('turns the API error shape into an ApiError with code, details and answer_id', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        apiError(503, 'verifier_not_configured', 'set VERIFIER_PROVIDER', { answer_id: 'a1' }),
      ),
    )

    const error = await apiRequest('/v1/verify', { method: 'POST', body: {} }).catch((e) => e)

    expect(error).toBeInstanceOf(ApiError)
    expect(toErrorPayload(error)).toEqual({
      status: 503,
      code: 'verifier_not_configured',
      message: 'set VERIFIER_PROVIDER',
      details: null,
      answerId: 'a1',
    })
  })

  it('handles an error response that is not in the API error shape', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => jsonResponse(503, { status: 'unavailable' })))
    const error = await apiRequest('/healthz', { auth: false }).catch((e) => e)
    expect([error.status, error.code]).toEqual([503, 'http_503'])
  })

  it('reports a network failure as status 0 / network_error', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => Promise.reject(new TypeError('Failed to fetch'))))
    const error = await apiRequest('/v1/audit-runs').catch((e) => e)
    expect([error.status, error.code]).toEqual([0, 'network_error'])
  })
})
