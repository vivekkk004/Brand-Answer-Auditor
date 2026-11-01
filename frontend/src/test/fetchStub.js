import { vi } from 'vitest'

/**
 * Replace fetch with a fake router: `routes` maps "METHOD /path" to a function that
 * returns a Response. Unknown requests fail the test loudly. Every call is recorded.
 */
export function stubFetch(routes) {
  const fetchMock = vi.fn(async (url, init = {}) => {
    const { pathname } = new URL(url, 'http://localhost')
    const key = `${init.method || 'GET'} ${pathname}`
    const handler = routes[key]
    if (!handler) throw new Error(`Unexpected request in test: ${key}`)
    return handler({ url: new URL(url, 'http://localhost'), init })
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}
