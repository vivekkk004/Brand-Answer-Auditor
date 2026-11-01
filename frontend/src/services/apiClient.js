/**
 * The ONE place in the app that calls fetch.
 *
 * Every service function goes through apiRequest, so the base URL, the Bearer key, JSON
 * handling and error parsing are written once. The backend always reports errors as
 * {"error": {"code", "message", ...}}; this file turns that into an ApiError.
 */

const BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')

// The store registers a function that returns the current API key. The client does not
// import the store, so there is no import cycle and tests can set any key they like.
let getApiKey = () => null

export function setApiKeyProvider(provider) {
  getApiKey = provider
}

export class ApiError extends Error {
  constructor({ status, code, message, details = null, answerId = null }) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
    this.answerId = answerId
  }
}

/** A plain object version of any error, safe to keep in Redux (errors are not serialisable). */
export function toErrorPayload(error) {
  if (error instanceof ApiError) {
    return {
      status: error.status,
      code: error.code,
      message: error.message,
      details: error.details,
      answerId: error.answerId,
    }
  }
  return { status: 0, code: 'client_error', message: error?.message || 'Something went wrong' }
}

function buildUrl(path, query) {
  const params = new URLSearchParams()
  for (const [name, value] of Object.entries(query || {})) {
    // Empty filters are left out, so "all statuses" is simply no status parameter.
    if (value !== undefined && value !== null && value !== '') params.set(name, String(value))
  }
  const search = params.toString()
  return `${BASE_URL}${path}${search ? `?${search}` : ''}`
}

async function readJson(response) {
  const text = await response.text()
  if (!text) return null
  try {
    return JSON.parse(text)
  } catch {
    return null
  }
}

function errorFromResponse(response, body) {
  const error = body?.error
  if (error) {
    return new ApiError({
      status: response.status,
      code: error.code,
      message: error.message,
      details: error.details ?? null,
      answerId: error.answer_id ?? null,
    })
  }
  return new ApiError({
    status: response.status,
    code: `http_${response.status}`,
    message: `The server answered ${response.status} ${response.statusText}`.trim(),
  })
}

/**
 * Send a request and return { data, status, headers }.
 *
 * Options:
 * - method, body (sent as JSON), query (object of URL parameters)
 * - idempotencyKey: sent as the Idempotency-Key header
 * - apiKey: use this key instead of the stored one (used to test a key before saving it)
 * - auth: false to send no key at all (health check)
 */
export async function apiRequestFull(path, options = {}) {
  const { method = 'GET', body, query, idempotencyKey, apiKey, auth = true, signal } = options
  const headers = { Accept: 'application/json' }
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (idempotencyKey) headers['Idempotency-Key'] = idempotencyKey
  const key = apiKey ?? getApiKey()
  if (auth && key) headers.Authorization = `Bearer ${key}`

  let response
  try {
    response = await fetch(buildUrl(path, query), {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal,
    })
  } catch {
    throw new ApiError({
      status: 0,
      code: 'network_error',
      message: 'Cannot reach the API. Check that it is running.',
    })
  }

  const data = await readJson(response)
  if (!response.ok) throw errorFromResponse(response, data)
  return { data, status: response.status, headers: response.headers }
}

/** Like apiRequestFull, but returns only the parsed body. */
export async function apiRequest(path, options) {
  const { data } = await apiRequestFull(path, options)
  return data
}
