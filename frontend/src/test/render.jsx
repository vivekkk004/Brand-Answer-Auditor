import { render } from '@testing-library/react'
import { Provider } from 'react-redux'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { setupStore } from '../app/store'
import { routes } from '../routes/routes'

/**
 * Render the real app (real routes, real store) at a URL. `apiKey` pre-connects the
 * user. Network calls go to whatever fetch the test stubbed.
 */
export function renderApp(url, { apiKey = null } = {}) {
  const store = setupStore({ auth: { apiKey, status: 'idle', error: null, sessionExpired: false } })
  const router = createMemoryRouter(routes, { initialEntries: [url] })
  const utils = render(
    <Provider store={store}>
      <RouterProvider router={router} />
    </Provider>,
  )
  return { ...utils, store, router }
}
