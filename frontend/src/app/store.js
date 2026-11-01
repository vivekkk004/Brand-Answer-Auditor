import { combineReducers, configureStore } from '@reduxjs/toolkit'
import answersReducer from '../features/answers/answersSlice'
import { saveApiKey } from '../features/auth/apiKeyStorage'
import authReducer from '../features/auth/authSlice'
import healthReducer from '../features/health/healthSlice'
import reviewReducer from '../features/review/reviewSlice'
import runsReducer from '../features/runs/runsSlice'
import verifyReducer from '../features/verify/verifySlice'
import { setApiKeyProvider } from '../services/apiClient'

const appReducer = combineReducers({
  auth: authReducer,
  health: healthReducer,
  runs: runsReducer,
  verify: verifyReducer,
  answers: answersReducer,
  review: reviewReducer,
})

// Signing out (or a 401) clears every slice, so one client's data never shows up for the
// next key entered in the same tab.
function rootReducer(state, action) {
  const next = appReducer(state, action)
  const signedOut = Boolean(state?.auth.apiKey) && !next.auth.apiKey
  if (!signedOut) return next
  // Keep the auth slice: it records why (logout or an expired session).
  return { ...appReducer(undefined, { type: '@@app/reset' }), auth: next.auth }
}

/** Build a store. Tests pass `preloadedState` to start from a known state. */
export function setupStore(preloadedState) {
  const store = configureStore({ reducer: rootReducer, preloadedState })

  // The API client asks the store for the key; the store remembers it in sessionStorage.
  setApiKeyProvider(() => store.getState().auth.apiKey)
  let lastKey = store.getState().auth.apiKey
  store.subscribe(() => {
    const key = store.getState().auth.apiKey
    if (key !== lastKey) {
      lastKey = key
      saveApiKey(key)
    }
  })
  return store
}
