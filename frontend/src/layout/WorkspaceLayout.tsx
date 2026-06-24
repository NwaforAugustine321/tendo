import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { MessageSquare } from 'lucide-react'
import { IconRail } from '../components/containers'
import { TopBar } from '../components/containers'
import { ChatPanel } from '../components/containers/ChatPanel'
import { FolderNavigation } from '../components/containers/FolderNavigation'
import { RadialMenu } from '../components/containers/RadialMenu'
import { WorkspaceContent } from '../components/containers/WorkspaceContent'
import { QuickActionButton } from '../components/atoms/QuickActionButton'
import { useWorkspaceStore } from '../store/workspace'
import { primaryFromPathname, type PrimarySection } from '../lib/navigation'

export function WorkspaceLayout() {
  const location = useLocation()
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  const [chatPanelVisible, setChatPanelVisible] = useState(true)
  const [folderNavPinned, setFolderNavPinned] = useState(true)
  const hoverClearTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const { radialMenuOpen, openRadialMenu, activeRecordId } = useWorkspaceStore()

  const routePrimary: PrimarySection = useMemo(
    () => primaryFromPathname(location.pathname),
    [location.pathname]
  )

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

  return (
    <div className="flex h-dvh max-h-dvh flex-col overflow-hidden bg-[#0a0a0a] text-zinc-100">
      {/* Top bar */}
      <TopBar onMenuClick={() => setMobileNavOpen(true)} />

      <div className="flex min-h-0 min-w-0 flex-1">
        {/* Primary icon rail + Folder Navigation — desktop */}
        <div
          className="relative hidden min-h-0 max-h-full md:flex"
          onMouseEnter={cancelHoverClear}
          onMouseLeave={scheduleHoverClear}
        >
          <div className="relative w-[52px] shrink-0 self-stretch min-h-0">
            <IconRail
              activePrimary={routePrimary}
              onPrimaryClick={onPrimaryClick}
              onToggleSecondary={() => setFolderNavPinned(!folderNavPinned)}
              secondaryVisible={folderNavPinned}
            />
          </div>
          {folderNavPinned && (
            <div className="w-[260px] min-h-0 overflow-hidden border-r border-zinc-800/60 bg-[#0f0f0f]">
              <FolderNavigation />
            </div>
          )}

          {/* Quick Action Button — positioned at right edge of sidebar panel */}
          <QuickActionButton onClick={openRadialMenu} visible={!radialMenuOpen} />
        </div>

        {/* Main content — either workspace content or route outlet */}
        <main className="min-h-0 min-w-0 flex-1 overflow-y-auto border-l border-zinc-800/60 bg-[#0a0a0a] px-3 py-5 sm:px-5 sm:py-6 lg:px-8">
          <div className="flex min-h-0 w-full min-w-0 max-w-4xl flex-col justify-start h-full">
            <WorkspaceContent />
          </div>
        </main>

        {/* Chat panel — right side (toggleable via edge border button) */}
        <div className="hidden min-h-0 lg:flex relative">
          <button
            type="button"
            onClick={() => setChatPanelVisible(!chatPanelVisible)}
            className="absolute left-0 top-1/2 -translate-x-1/2 -translate-y-1/2 z-10 flex h-6 w-6 items-center justify-center rounded-full border border-zinc-700 bg-[#1a1a1a] text-zinc-400 transition-colors hover:border-zinc-500 hover:text-zinc-200"
            title={chatPanelVisible ? 'Close chat' : 'Open chat'}
          >
            <MessageSquare size={10} />
          </button>
          {chatPanelVisible ? (
            <ChatPanel />
          ) : (
            <div className="w-5 border-l border-zinc-800/60 bg-[#0f0f0f]" />
          )}
        </div>
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

      {/* Radial Hub Menu */}
      <RadialMenu />
    </div>
  )
}
