import AppLayout from '../components/layout/AppLayout'
import PublicLayout from '../components/layout/PublicLayout'
import AnswerPage from '../pages/AnswerPage'
import ConnectPage from '../pages/ConnectPage'
import DashboardPage from '../pages/DashboardPage'
import LandingPage from '../pages/LandingPage'
import NewRunPage from '../pages/NewRunPage'
import NotFoundPage from '../pages/NotFoundPage'
import ReviewQueuePage from '../pages/ReviewQueuePage'
import RunDetailPage from '../pages/RunDetailPage'
import RunsPage from '../pages/RunsPage'
import VerifyPage from '../pages/VerifyPage'
import ProtectedRoute from './ProtectedRoute'
import { PATHS } from './paths'

/**
 * The route table. Public pages share PublicLayout; app pages sit behind ProtectedRoute
 * (needs an API key) and share AppLayout (sidebar + top bar).
 * Kept separate from the router so tests can mount it in a memory router.
 */
export const routes = [
  {
    element: <PublicLayout />,
    children: [
      { path: PATHS.home, element: <LandingPage /> },
      { path: PATHS.connect, element: <ConnectPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
  {
    path: PATHS.app,
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppLayout />,
        children: [
          { index: true, element: <DashboardPage /> },
          { path: 'runs', element: <RunsPage /> },
          { path: 'runs/new', element: <NewRunPage /> },
          { path: 'runs/:runId', element: <RunDetailPage /> },
          { path: 'verify', element: <VerifyPage /> },
          { path: 'answers/:answerId', element: <AnswerPage /> },
          { path: 'review', element: <ReviewQueuePage /> },
        ],
      },
    ],
  },
]
