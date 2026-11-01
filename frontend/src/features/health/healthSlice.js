import { createSlice } from '@reduxjs/toolkit'
import { createApiThunk } from '../../app/createApiThunk'
import { getHealth } from '../../services/healthService'

export const fetchHealth = createApiThunk('health/fetch', () => getHealth())

const healthSlice = createSlice({
  name: 'health',
  // 'unknown' until the first check; then 'ok' or 'down'.
  initialState: { state: 'unknown', status: 'idle', checkedAt: null },
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchHealth.pending, (state) => {
        state.status = 'loading'
      })
      .addCase(fetchHealth.fulfilled, (state, action) => {
        state.status = 'succeeded'
        state.state = action.payload?.status === 'ok' ? 'ok' : 'down'
        state.checkedAt = new Date().toISOString()
      })
      .addCase(fetchHealth.rejected, (state) => {
        state.status = 'failed'
        state.state = 'down'
        state.checkedAt = new Date().toISOString()
      })
  },
})

export default healthSlice.reducer
