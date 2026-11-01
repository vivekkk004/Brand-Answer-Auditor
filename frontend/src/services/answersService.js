import { apiRequest } from './apiClient'

/** GET /v1/answers/{id} — the answer, its claims and the agent conversation. */
export function getAnswer(answerId) {
  return apiRequest(`/v1/answers/${encodeURIComponent(answerId)}`)
}
