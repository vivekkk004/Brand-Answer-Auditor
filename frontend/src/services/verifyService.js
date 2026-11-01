import { apiRequest } from './apiClient'

/** POST /v1/verify — check one answer now. Returns the saved answer with its claims. */
export function verifyText({ text, market, promptVersion = 'v1' }) {
  const body = { text, prompt_version: promptVersion }
  if (market) body.market = market
  return apiRequest('/v1/verify', { method: 'POST', body })
}
