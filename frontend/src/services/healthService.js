import { apiRequest } from './apiClient'

/** GET /healthz — the API is up and can reach its database. Needs no key. */
export function getHealth() {
  return apiRequest('/healthz', { auth: false })
}
