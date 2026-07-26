import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { TopBar } from '../components/containers'
import { Sidebar } from '../components/containers/Sidebar'
import { RightRail } from '../components/containers/RightRail'
import { TalkingCharacter } from '../components/containers/TalkingCharacter'
import { ChatPanel } from '../components/containers/ChatPanel'
import { FloatingPanel } from '../components/containers/FloatingPanel'
import { WorkspaceContent } from '../components/containers/WorkspaceContent'
import { RecordFloatingPanel } from '../components/containers/RecordFloatingPanel'
import { ProcessingNotification } from '../components/atoms/ProcessingNotification'
import { useWorkspaceStore } from '../store/workspace'

export function WorkspaceLayout() {
  const location = useLocation()
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(true)
  const [chatPanelVisible, setChatPanelVisible] = useState(true)

  const {
    dashboardChatVisible,
    toggleDashboardSidebar,
  } = useWorkspaceStore()

  // Detect if we're on the dashboard (home) route
  const isDashboard = location.pathname === '/app' || location.pathname === '/app/'

  // Resolve chat visibility based on whether we're on dashboard
  const effectiveChatVisible = isDashboard ? dashboardChatVisible : chatPanelVisible

  useEffect(() => {
    const handleOpenChat = () => setChatPanelVisible(true)
    window.addEventListener('tendo:open-chat', handleOpenChat)
    return () => window.removeEventListener('tendo:open-chat', handleOpenChat)
  }, [])

  const pendingChatMessage = useWorkspaceStore((s) => s.pendingChatMessage)

  useEffect(() => {
    if (pendingChatMessage) {
      setChatPanelVisible(true)
    }
  }, [pendingChatMessage])

  return (
    <div className="flex h-dvh max-h-dvh flex-col overflow-hidden bg-[#0a0a0a] text-zinc-100">
      {/* Top bar — unchanged */}
      <TopBar onMenuClick={() => {
        if (isDashboard) {
          toggleDashboardSidebar()
        } else {
          setMobileNavOpen(true)
        }
      }} />

      <div className="flex min-h-0 min-w-0 flex-1">
        {/* Gmail-style collapsible left sidebar — desktop */}
        <div className="hidden md:flex min-h-0 max-h-full">
          <Sidebar
            collapsed={sidebarCollapsed}
            onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
          />
        </div>

        {/* Main content area */}
        <main className="min-h-0 min-w-0 flex-1 overflow-y-auto bg-[#0a0a0a]">
          <div className="flex min-h-0 w-full min-w-0 flex-col justify-start h-full">
            <WorkspaceContent />
          </div>
        </main>

        {/* Gmail-style right sidebar rail */}
        <RightRail onPlusClick={() => {
          if (isDashboard) {
            useWorkspaceStore.getState().toggleDashboardChat()
          } else {
            setChatPanelVisible(true)
          }
        }} />

        {/* Right panel — Floating draggable Chat */}
        <FloatingPanel
          visible={effectiveChatVisible}
          title="Sessions"
          onClose={() => {
            if (isDashboard) {
              useWorkspaceStore.getState().toggleDashboardChat()
            } else {
              setChatPanelVisible(false)
            }
          }}
        >
          <div className="min-h-0 flex-1 flex flex-col overflow-hidden">
            <ChatPanel />
          </div>
        </FloatingPanel>

        {/* Record floating panel — independent, draggable */}
        <RecordFloatingPanel />
      </div>

      {/* Mobile nav overlay */}
      {mobileNavOpen && (
        <>
          <button
            type="button"
            className="fixed inset-0 z-40 bg-black/70 md:hidden"
            aria-label="Close menu"
            onClick={() => setMobileNavOpen(false)}
          />
          <div className="fixed inset-y-0 left-0 z-50 flex w-[min(280px,92vw)] flex-col border-r border-zinc-800/90 bg-[#0f0f0f] shadow-2xl md:hidden">
            <Sidebar
              className="w-full"
              collapsed={false}
              onToggle={() => setMobileNavOpen(false)}
            />
          </div>
        </>
      )}

      {/* Processing notifications — top right corner */}
      <ProcessingNotification />
    </div>
  )
}
