import { createSlice } from '@reduxjs/toolkit'
import { createApiThunk } from '../../app/createApiThunk'
import * as runsService from '../../services/runsService'

export const PAGE_SIZE = 20

export const fetchRuns = createApiThunk('runs/fetchList', (query) => runsService.listRuns(query))

export const fetchRecentRuns = createApiThunk('runs/fetchRecent', () =>
  runsService.listRuns({ limit: 5 }),
)

export const fetchRun = createApiThunk('runs/fetchOne', (runId) => runsService.getRun(runId))

export const createRun = createApiThunk('runs/create', ({ config, idempotencyKey }) =>
  runsService.createRun(config, idempotencyKey),
)

const initialState = {
  // The Runs page table.
  list: { items: [], status: 'idle', error: null, filter: '', offset: 0, limit: PAGE_SIZE },
  // The dashboard's "recent runs" card (kept apart so it never fights the table).
  recent: { items: [], status: 'idle', error: null },
  // Runs by ID, for the detail page and its polling.
  byId: {},
  detail: { status: 'idle', error: null },
  // The New run form.
  create: { status: 'idle', error: null, replayed: false, runId: null },
}

const runsSlice = createSlice({
  name: 'runs',
  initialState,
  reducers: {
    setRunsFilter(state, action) {
      state.list.filter = action.payload
      state.list.offset = 0
    },
    setRunsOffset(state, action) {
      state.list.offset = Math.max(0, action.payload)
    },
    resetCreate(state) {
      state.create = initialState.create
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchRuns.pending, (state) => {
        state.list.status = 'loading'
        state.list.error = null
      })
      .addCase(fetchRuns.fulfilled, (state, action) => {
        state.list.status = 'succeeded'
        state.list.items = action.payload.items
        for (const run of action.payload.items) state.byId[run.id] = run
      })
      .addCase(fetchRuns.rejected, (state, action) => {
        state.list.status = 'failed'
        state.list.error = action.payload
      })

      .addCase(fetchRecentRuns.pending, (state) => {
        state.recent.status = 'loading'
        state.recent.error = null
      })
      .addCase(fetchRecentRuns.fulfilled, (state, action) => {
        state.recent.status = 'succeeded'
        state.recent.items = action.payload.items
      })
      .addCase(fetchRecentRuns.rejected, (state, action) => {
        state.recent.status = 'failed'
        state.recent.error = action.payload
      })

      .addCase(fetchRun.pending, (state) => {
        state.detail.status = 'loading'
        state.detail.error = null
      })
      .addCase(fetchRun.fulfilled, (state, action) => {
        state.detail.status = 'succeeded'
        state.byId[action.payload.id] = action.payload
      })
      .addCase(fetchRun.rejected, (state, action) => {
        state.detail.status = 'failed'
        state.detail.error = action.payload
      })

      .addCase(createRun.pending, (state) => {
        state.create.status = 'loading'
        state.create.error = null
      })
      .addCase(createRun.fulfilled, (state, action) => {
        const { run, replayed } = action.payload
        state.create = { status: 'succeeded', error: null, replayed, runId: run.id }
        state.byId[run.id] = run
      })
      .addCase(createRun.rejected, (state, action) => {
        state.create.status = 'failed'
        state.create.error = action.payload
      })
  },
})

export const { setRunsFilter, setRunsOffset, resetCreate } = runsSlice.actions
export default runsSlice.reducer

export const selectRunById = (runId) => (state) => state.runs.byId[runId]
