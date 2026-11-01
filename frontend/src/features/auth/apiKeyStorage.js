/**
 * The API key lives in sessionStorage: it survives a page reload but is gone when the tab
 * closes. Storage can be blocked (private mode, strict settings), so every access is
 * wrapped and the app still works, just without remembering the key.
 */
const STORAGE_KEY = 'baa.apiKey'

export function loadApiKey() {
  try {
    return window.sessionStorage.getItem(STORAGE_KEY)
  } catch {
    return null
  }
}

export function saveApiKey(apiKey) {
  try {
    if (apiKey) window.sessionStorage.setItem(STORAGE_KEY, apiKey)
    else window.sessionStorage.removeItem(STORAGE_KEY)
  } catch {
    // Not remembered; the user enters the key again next time.
  }
}
