import { apiRequest, apiRequestFull } from './apiClient'

/** GET /v1/audit-runs — the caller's runs, newest first. */
export function listRuns({ status, limit = 20, offset = 0 } = {}) {
  return apiRequest('/v1/audit-runs', { query: { status, limit, offset } })
}

/** GET /v1/audit-runs/{id} — status, config and metrics of one run. */
export function getRun(runId) {
  return apiRequest(`/v1/audit-runs/${encodeURIComponent(runId)}`)
}

/**
 * POST /v1/audit-runs — queue a run.
 * The same idempotencyKey with the same config returns the existing run (200 + replay
 * header) instead of starting a second, paid run.
 */
export async function createRun(config, idempotencyKey) {
  const { data, headers } = await apiRequestFull('/v1/audit-runs', {
    method: 'POST',
    body: config,
    idempotencyKey,
  })
  return { run: data, replayed: headers.get('Idempotent-Replayed') === 'true' }
}
