import { Routes, Route, Navigate } from 'react-router-dom'
import { Landing } from './pages/Landing'
import { Onboarding } from './pages/Onboarding'
import { Conversation } from './pages/Conversation'
import { WorkspaceLayout } from './layout/WorkspaceLayout'
import { WorkspaceHome } from './pages/workspace/Home'
import { Business } from './pages/workspace/Business'
import { Inventory } from './pages/workspace/Inventory'
import { Customers } from './pages/workspace/Customers'
import { Analytics } from './pages/workspace/Analytics'

export default function App() {
  return (
    <Routes>
      {/* Public */}
      <Route path="/" element={<Landing />} />
      <Route path="/onboarding" element={<Onboarding />} />

      {/* Workspace — dashboard with icon rail */}
      <Route path="/app" element={<WorkspaceLayout />}>
        <Route index element={<WorkspaceHome />} />
        <Route path="conversation/new" element={<Conversation />} />
        <Route path="conversation/:sessionId" element={<Conversation />} />
        <Route path="business" element={<Business />} />
        <Route path="inventory" element={<Inventory />} />
        <Route path="customers" element={<Customers />} />
        <Route path="analytics" element={<Analytics />} />
      </Route>

      {/* Fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
