import { createSlice, isRejected } from '@reduxjs/toolkit'
import { createApiThunk } from '../../app/createApiThunk'
import { listReviewItems } from '../../services/reviewService'
import { loadApiKey } from './apiKeyStorage'

const KEY_PATTERN = /^baa_[A-Za-z0-9_-]+$/

/**
 * Test a key with a cheap authenticated request before saving it, so a typo is caught on
 * the connect screen instead of on the first real page.
 */
export const connect = createApiThunk('auth/connect', async (rawKey) => {
  const apiKey = rawKey.trim()
  if (!KEY_PATTERN.test(apiKey)) {
    // Checked here so a typo never reaches the server; shown like any other error.
    throw new Error('An API key starts with "baa_" and has no spaces.')
  }
  await listReviewItems({ limit: 1 }, { apiKey })
  return apiKey
})

const initialState = {
  apiKey: loadApiKey(),
  status: 'idle',
  error: null,
  // True when a request was refused with 401 (for example the key was revoked).
  sessionExpired: false,
}

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    logout(state) {
      state.apiKey = null
      state.status = 'idle'
      state.error = null
      state.sessionExpired = false
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(connect.pending, (state) => {
        state.status = 'loading'
        state.error = null
      })
      .addCase(connect.fulfilled, (state, action) => {
        state.status = 'succeeded'
        state.apiKey = action.payload
        state.sessionExpired = false
      })
      .addCase(connect.rejected, (state, action) => {
        state.status = 'failed'
        state.error =
          action.payload?.status === 401
            ? { ...action.payload, message: 'That API key was not accepted.' }
            : action.payload
      })
      // Any other request refused with 401 means the stored key no longer works:
      // sign out in one place instead of in every page.
      .addMatcher(
        (action) => isRejected(action) && action.type !== connect.rejected.type,
        (state, action) => {
          if (action.payload?.status === 401 && state.apiKey) {
            state.apiKey = null
            state.sessionExpired = true
          }
        },
      )
  },
})

export const { logout } = authSlice.actions
export default authSlice.reducer

export const selectApiKey = (state) => state.auth.apiKey
export const selectIsAuthenticated = (state) => Boolean(state.auth.apiKey)
