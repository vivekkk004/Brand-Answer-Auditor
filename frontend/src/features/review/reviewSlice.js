import { createSlice } from '@reduxjs/toolkit'
import { createApiThunk } from '../../app/createApiThunk'
import * as reviewService from '../../services/reviewService'

export const PAGE_SIZE = 20
// The API returns at most 200 items per page; the dashboard shows "200+" beyond that.
export const OPEN_COUNT_LIMIT = 200

export const fetchReviewItems = createApiThunk('review/fetchList', (query) =>
  reviewService.listReviewItems(query),
)

export const fetchOpenReviewCount = createApiThunk('review/fetchOpenCount', async () => {
  const page = await reviewService.listReviewItems({ status: 'open', limit: OPEN_COUNT_LIMIT })
  return page.items.length
})

export const decideReviewItem = createApiThunk('review/decide', ({ id, decision, note }) =>
  reviewService.decideReviewItem(id, { decision, note }),
)

const initialState = {
  items: [],
  status: 'idle',
  error: null,
  filter: 'open',
  offset: 0,
  limit: PAGE_SIZE,
  openCount: { value: null, status: 'idle' },
  // The item being decided right now, and the last decision error (with its item).
  decide: { pendingId: null, error: null, itemId: null },
}

const reviewSlice = createSlice({
  name: 'review',
  initialState,
  reducers: {
    setReviewFilter(state, action) {
      state.filter = action.payload
      state.offset = 0
    },
    setReviewOffset(state, action) {
      state.offset = Math.max(0, action.payload)
    },
    clearDecideError(state) {
      state.decide.error = null
      state.decide.itemId = null
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchReviewItems.pending, (state) => {
        state.status = 'loading'
        state.error = null
      })
      .addCase(fetchReviewItems.fulfilled, (state, action) => {
        state.status = 'succeeded'
        state.items = action.payload.items
      })
      .addCase(fetchReviewItems.rejected, (state, action) => {
        state.status = 'failed'
        state.error = action.payload
      })

      .addCase(fetchOpenReviewCount.pending, (state) => {
        state.openCount.status = 'loading'
      })
      .addCase(fetchOpenReviewCount.fulfilled, (state, action) => {
        state.openCount = { value: action.payload, status: 'succeeded' }
      })
      .addCase(fetchOpenReviewCount.rejected, (state) => {
        state.openCount.status = 'failed'
      })

      .addCase(decideReviewItem.pending, (state, action) => {
        state.decide = { pendingId: action.meta.arg.id, error: null, itemId: null }
      })
      .addCase(decideReviewItem.fulfilled, (state, action) => {
        const decided = action.payload
        state.decide.pendingId = null
        // On the "open" tab a decided item no longer belongs; elsewhere, update it in place.
        state.items =
          state.filter === 'open'
            ? state.items.filter((item) => item.id !== decided.id)
            : state.items.map((item) => (item.id === decided.id ? decided : item))
        if (state.openCount.value !== null && state.openCount.value > 0) {
          state.openCount.value -= 1
        }
      })
      .addCase(decideReviewItem.rejected, (state, action) => {
        state.decide = { pendingId: null, error: action.payload, itemId: action.meta.arg.id }
      })
  },
})

export const { setReviewFilter, setReviewOffset, clearDecideError } = reviewSlice.actions
export default reviewSlice.reducer
