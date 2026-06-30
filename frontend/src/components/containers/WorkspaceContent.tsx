import { useLocation } from 'react-router-dom'
import { InsightsFeed } from './InsightsFeed'
import { Dashboard } from '../../pages/workspace/Dashboard'

export function WorkspaceContent() {
  const location = useLocation()
  const isDashboard = location.pathname === '/app' || location.pathname === '/app/'

  if (isDashboard) {
    return <Dashboard />
  }

  return <InsightsFeed />
}
