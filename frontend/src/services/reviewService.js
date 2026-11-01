import { apiRequest } from './apiClient'

/**
 * GET /v1/review-items — review items with their claims.
 * `apiKey` lets the connect screen test a key before it is saved.
 */
export function listReviewItems({ status, limit = 20, offset = 0 } = {}, { apiKey } = {}) {
  return apiRequest('/v1/review-items', { query: { status, limit, offset }, apiKey })
}

/** PATCH /v1/review-items/{id} — confirm or dismiss once. A second decision is a 409. */
export function decideReviewItem(itemId, { decision, note }) {
  return apiRequest(`/v1/review-items/${encodeURIComponent(itemId)}`, {
    method: 'PATCH',
    body: { decision, note: note?.trim() ? note.trim() : null },
  })
}
