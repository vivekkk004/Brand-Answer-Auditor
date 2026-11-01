import { describe, expect, it } from 'vitest'
import { setupStore } from '../../app/store'
import { apiError, jsonResponse, makeRun } from '../../test/fixtures'
import { stubFetch } from '../../test/fetchStub'
import { fetchRuns } from '../runs/runsSlice'
import { connect, logout } from './authSlice'

function signedInStore() {
  return setupStore({ auth: { apiKey: 'baa_old', status: 'idle', error: null, sessionExpired: false } })
}

describe('auth', () => {
  it('rejects a malformed key without calling the API', async () => {
    const fetchMock = stubFetch({})
    const store = setupStore()

    await store.dispatch(connect('not a key'))

    expect(fetchMock).not.toHaveBeenCalled()
    expect(store.getState().auth.status).toBe('failed')
    expect(store.getState().auth.error.message).toMatch(/starts with "baa_"/)
  })

  it('checks the key with the API before saving it', async () => {
    const fetchMock = stubFetch({
      'GET /v1/review-items': () => jsonResponse(200, { items: [], limit: 1, offset: 0 }),
    })
    const store = setupStore()

    await store.dispatch(connect('  baa_good-key  '))

    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBe('Bearer baa_good-key')
    expect(store.getState().auth.apiKey).toBe('baa_good-key')
    expect(window.sessionStorage.getItem('baa.apiKey')).toBe('baa_good-key')
  })

  it('shows a clear message when the API refuses the key', async () => {
    stubFetch({ 'GET /v1/review-items': () => apiError(401, 'unauthorized', 'missing or invalid API key') })
    const store = setupStore()

    await store.dispatch(connect('baa_wrong'))

    expect(store.getState().auth.apiKey).toBeNull()
    expect(store.getState().auth.error.message).toBe('That API key was not accepted.')
  })

  it('signs out when any request is refused with 401', async () => {
    stubFetch({ 'GET /v1/audit-runs': () => apiError(401, 'unauthorized', 'missing or invalid API key') })
    const store = signedInStore()

    await store.dispatch(fetchRuns({}))

    expect(store.getState().auth.apiKey).toBeNull()
    expect(store.getState().auth.sessionExpired).toBe(true)
  })

  it('does not sign out on other errors', async () => {
    stubFetch({ 'GET /v1/audit-runs': () => apiError(500, 'internal_error', 'boom') })
    const store = signedInStore()

    await store.dispatch(fetchRuns({}))

    expect(store.getState().auth.apiKey).toBe('baa_old')
  })

  it('clears every other slice on logout, so no data leaks to the next key', async () => {
    stubFetch({ 'GET /v1/audit-runs': () => jsonResponse(200, { items: [makeRun()], limit: 20, offset: 0 }) })
    const store = signedInStore()
    await store.dispatch(fetchRuns({}))
    expect(store.getState().runs.list.items).toHaveLength(1)

    store.dispatch(logout())

    expect(store.getState().runs.list.items).toEqual([])
    expect(store.getState().runs.byId).toEqual({})
    expect(window.sessionStorage.getItem('baa.apiKey')).toBeNull()
  })
})
