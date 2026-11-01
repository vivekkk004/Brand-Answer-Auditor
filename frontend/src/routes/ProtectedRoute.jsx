import { useSelector } from 'react-redux'
import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { selectIsAuthenticated } from '../features/auth/authSlice'
import { PATHS } from './paths'

/** App pages need an API key. Without one, go to /connect and come back afterwards. */
export default function ProtectedRoute() {
  const isAuthenticated = useSelector(selectIsAuthenticated)
  const location = useLocation()

  if (!isAuthenticated) {
    return <Navigate to={PATHS.connect} replace state={{ from: location.pathname }} />
  }
  return <Outlet />
}
