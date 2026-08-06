import { useLocation } from 'react-router-dom'
import { InsightsFeed } from './InsightsFeed'
import { Inbox } from '../../pages/workspace/inbox'
import { Dashboard } from '../../pages/workspace/Dashboard'

export function WorkspaceContent() {
  const location = useLocation()
  const path = location.pathname

  if (path === '/app' || path === '/app/') {
    return <Inbox />
  }

  if (path.startsWith('/app/insights')) {
    return <Dashboard />
  }

  return <InsightsFeed />
}
