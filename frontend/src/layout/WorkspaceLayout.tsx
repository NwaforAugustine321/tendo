import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { MessageSquare, Sparkles } from 'lucide-react'
import { IconRail } from '../components/containers'
import { TopBar } from '../components/containers'
import { TalkingCharacter } from '../components/containers/TalkingCharacter'
import { ChatPanel } from '../components/containers/ChatPanel'
import { FloatingPanel } from '../components/containers/FloatingPanel'
import { FolderNavigation } from '../components/containers/FolderNavigation'
import { WorkspaceContent } from '../components/containers/WorkspaceContent'
import { RecordInsightPanel } from '../components/containers/RecordInsightPanel'
import { ProcessingNotification } from '../components/atoms/ProcessingNotification'
import { useWorkspaceStore } from '../store/workspace'
import { primaryFromPathname, type PrimarySection } from '../lib/navigation'

export function WorkspaceLayout() {
  const location = useLocation()
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  const [chatPanelVisible, setChatPanelVisible] = useState(true)
  const [folderNavPinned, setFolderNavPinned] = useState(false)
  const [rightTab, setRightTab] = useState<'chat' | 'insight'>('chat')
  const hoverClearTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const {
    activeRecordId,
    dashboardSidebarVisible,
    dashboardChatVisible,
    toggleDashboardSidebar,
  } = useWorkspaceStore()

  // Detect if we're on the dashboard (home) route
  const isDashboard = location.pathname === '/app' || location.pathname === '/app/'

  const routePrimary: PrimarySection = useMemo(
    () => primaryFromPathname(location.pathname),
    [location.pathname]
  )

  // Resolve sidebar and chat visibility based on whether we're on dashboard
  const effectiveSidebarVisible = isDashboard ? dashboardSidebarVisible : folderNavPinned
  const effectiveChatVisible = isDashboard ? dashboardChatVisible : chatPanelVisible

  const cancelHoverClear = useCallback(() => {
    if (hoverClearTimer.current !== null) {
      clearTimeout(hoverClearTimer.current)
      hoverClearTimer.current = null
    }
  }, [])

  const scheduleHoverClear = useCallback(() => {
    cancelHoverClear()
    hoverClearTimer.current = setTimeout(() => {
      hoverClearTimer.current = null
    }, 220)
  }, [cancelHoverClear])

  const onPrimaryClick = useCallback(() => {
    setFolderNavPinned(true)
    cancelHoverClear()
  }, [cancelHoverClear])

  useEffect(() => () => cancelHoverClear(), [cancelHoverClear])

  useEffect(() => {
    const handleOpenChat = () => setChatPanelVisible(true)
    window.addEventListener('tendo:open-chat', handleOpenChat)
    return () => window.removeEventListener('tendo:open-chat', handleOpenChat)
  }, [])

  useEffect(() => {
    const handleOpenSidebar = () => setFolderNavPinned(true)
    window.addEventListener('tendo:open-sidebar', handleOpenSidebar)
    return () => window.removeEventListener('tendo:open-sidebar', handleOpenSidebar)
  }, [])

  useEffect(() => {
    if (activeRecordId) {
      setRightTab('insight')
      setChatPanelVisible(true)
    }
  }, [activeRecordId])

  const pendingChatMessage = useWorkspaceStore((s) => s.pendingChatMessage)

  useEffect(() => {
    if (pendingChatMessage) {
      setRightTab('chat')
      setChatPanelVisible(true)
    }
  }, [pendingChatMessage])

  return (
    <div className="flex h-dvh max-h-dvh flex-col overflow-hidden bg-[#0a0a0a] text-zinc-100">
      {/* Top bar */}
      <TopBar onMenuClick={() => {
        if (isDashboard) {
          toggleDashboardSidebar()
        } else {
          setMobileNavOpen(true)
        }
      }} />

      <div className="flex min-h-0 min-w-0 flex-1">
        {/* Primary icon rail + Folder Navigation — desktop */}
        <div
          className="group/sidebar relative hidden min-h-0 max-h-full md:flex"
          onMouseEnter={cancelHoverClear}
          onMouseLeave={scheduleHoverClear}
        >
          <div className="relative w-[52px] shrink-0 self-stretch min-h-0">
            <IconRail
              activePrimary={routePrimary}
              onPrimaryClick={onPrimaryClick}
              onToggleSecondary={() => {
                if (isDashboard) {
                  toggleDashboardSidebar()
                } else {
                  setFolderNavPinned(!folderNavPinned)
                }
              }}
              secondaryVisible={effectiveSidebarVisible}
            />
          </div>
          {effectiveSidebarVisible && (
            <div className="w-[260px] min-h-0 overflow-hidden border-r border-zinc-800/60 bg-[#0f0f0f]">
              <FolderNavigation />
            </div>
          )}
        </div>

        {/* Main content — either workspace content or route outlet */}
        <main className="min-h-0 min-w-0 flex-1 overflow-y-auto border-l border-zinc-800/60 bg-[#0a0a0a]">
          <div className="flex min-h-0 w-full min-w-0 flex-col justify-start h-full">
            <WorkspaceContent />
          </div>
        </main>

        {/* Right panel — Floating draggable Chat + Agent Insight */}
        <FloatingPanel
          visible={effectiveChatVisible}
          title={rightTab === 'chat' ? 'Sessions' : 'Insights'}
          onClose={() => {
            if (isDashboard) {
              useWorkspaceStore.getState().toggleDashboardChat()
            } else {
              setChatPanelVisible(false)
            }
          }}
        >
          {/* Tab bar */}
          <div className="flex border-b border-zinc-800/60 bg-[#0a0a0a] shrink-0">
            <button
              type="button"
              onClick={() => setRightTab('chat')}
              className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-[11px] font-medium transition-colors ${rightTab === 'chat' ? 'text-zinc-200 border-b-2 border-[#3ecf8e]' : 'text-zinc-500 hover:text-zinc-300'}`}
            >
              <MessageSquare size={11} />
              Sessions
            </button>
            <button
              type="button"
              onClick={() => setRightTab('insight')}
              className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-[11px] font-medium transition-colors ${rightTab === 'insight' ? 'text-zinc-200 border-b-2 border-[#3ecf8e]' : 'text-zinc-500 hover:text-zinc-300'}`}
            >
              <Sparkles size={11} />
              Insight
            </button>
          </div>
          {/* Tab content */}
          <div className="min-h-0 flex-1 flex flex-col overflow-hidden">
            {rightTab === 'chat' ? <ChatPanel /> : <RecordInsightPanel />}
          </div>
        </FloatingPanel>
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
          <div className="fixed inset-y-0 left-0 z-50 flex w-[min(300px,92vw)] flex-col border-r border-zinc-800/90 bg-[#111111] shadow-2xl md:hidden">
            <IconRail
              orientation="horizontal"
              activePrimary={routePrimary}
              onPrimaryClick={onPrimaryClick}
              onNavigate={() => setMobileNavOpen(false)}
            />
            <div className="min-h-0 flex-1 overflow-y-auto">
              <FolderNavigation />
            </div>
          </div>
        </>
      )}

      {/* Dashboard character — bottom-left, facing right */}
      {isDashboard && (
        <div className="pointer-events-none">
          <TalkingCharacter isSpeaking={false} flipX={true} leftOffset={effectiveSidebarVisible ? 200 : -30} />
        </div>
      )}

      {/* Processing notifications — top right corner */}
      <ProcessingNotification />
    </div>
  )
}
