import { describe, expect, it } from 'vitest'
import { setupStore } from '../../app/store'
import { apiError, jsonResponse, makeReviewItem } from '../../test/fixtures'
import { stubFetch } from '../../test/fetchStub'
import { decideReviewItem, fetchReviewItems } from './reviewSlice'

const signedIn = { auth: { apiKey: 'baa_k', status: 'idle', error: null, sessionExpired: false } }
const ITEM = makeReviewItem()

async function storeWithOneOpenItem() {
  const store = setupStore(signedIn)
  stubFetch({
    'GET /v1/review-items': () => jsonResponse(200, { items: [ITEM], limit: 20, offset: 0 }),
    [`PATCH /v1/review-items/${ITEM.id}`]: ({ init }) => {
      const body = JSON.parse(init.body)
      return jsonResponse(200, { ...ITEM, status: body.decision, note: body.note })
    },
  })
  await store.dispatch(fetchReviewItems({ status: 'open' }))
  return store
}

describe('review slice', () => {
  it('removes a decided item from the open list and sends a trimmed note', async () => {
    const store = await storeWithOneOpenItem()

    await store.dispatch(decideReviewItem({ id: ITEM.id, decision: 'confirmed', note: '  wrong  ' }))

    expect(store.getState().review.items).toEqual([])
    expect(store.getState().review.decide.pendingId).toBeNull()
  })

  it('sends null for an empty note', async () => {
    const store = await storeWithOneOpenItem()
    const { payload } = await store.dispatch(
      decideReviewItem({ id: ITEM.id, decision: 'dismissed', note: '   ' }),
    )
    expect(payload.note).toBeNull()
  })

  it('keeps a 409 against the item it belongs to', async () => {
    const store = setupStore(signedIn)
    stubFetch({
      [`PATCH /v1/review-items/${ITEM.id}`]: () =>
        apiError(409, 'already_decided', 'this item was already confirmed'),
    })

    await store.dispatch(decideReviewItem({ id: ITEM.id, decision: 'dismissed' }))

    expect(store.getState().review.decide).toMatchObject({
      itemId: ITEM.id,
      error: { status: 409, code: 'already_decided' },
    })
  })
})
