import { describe, expect, it } from 'vitest'
import { setupStore } from '../../app/store'
import { apiError, jsonResponse, makeRun } from '../../test/fixtures'
import { stubFetch } from '../../test/fetchStub'
import { createRun, fetchRun, fetchRuns, setRunsFilter, setRunsOffset } from './runsSlice'

const signedIn = { auth: { apiKey: 'baa_k', status: 'idle', error: null, sessionExpired: false } }

describe('runs slice', () => {
  it('loads a page of runs and indexes them by ID', async () => {
    const fetchMock = stubFetch({
      'GET /v1/audit-runs': () => jsonResponse(200, { items: [makeRun()], limit: 20, offset: 40 }),
    })
    const store = setupStore(signedIn)

    await store.dispatch(fetchRuns({ status: 'queued', limit: 20, offset: 40 }))

    const url = new URL(fetchMock.mock.calls[0][0], 'http://localhost')
    expect(url.search).toBe('?status=queued&limit=20&offset=40')
    const state = store.getState().runs
    expect(state.list.status).toBe('succeeded')
    expect(state.byId[makeRun().id].status).toBe('queued')
  })

  it('keeps the API error payload when loading fails', async () => {
    stubFetch({ 'GET /v1/audit-runs/abc': () => apiError(404, 'not_found', 'audit run not found') })
    const store = setupStore(signedIn)

    await store.dispatch(fetchRun('abc'))

    expect(store.getState().runs.detail.error).toMatchObject({ status: 404, code: 'not_found' })
  })

  it('creates a run with the Idempotency-Key and reports a replay', async () => {
    const fetchMock = stubFetch({
      'POST /v1/audit-runs': () => jsonResponse(200, makeRun(), { 'Idempotent-Replayed': 'true' }),
    })
    const store = setupStore(signedIn)

    await store.dispatch(createRun({ config: { category: 'earbuds' }, idempotencyKey: 'ui-1' }))

    expect(fetchMock.mock.calls[0][1].headers['Idempotency-Key']).toBe('ui-1')
    expect(store.getState().runs.create).toMatchObject({
      status: 'succeeded',
      replayed: true,
      runId: makeRun().id,
    })
  })

  it('goes back to the first page when the filter changes', () => {
    const store = setupStore(signedIn)
    store.dispatch(setRunsOffset(40))
    store.dispatch(setRunsFilter('failed'))
    expect(store.getState().runs.list).toMatchObject({ filter: 'failed', offset: 0 })
  })
})
