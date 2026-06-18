import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { IconRail } from '../components/containers'
import { SecondaryNav } from '../components/containers'
import { TopBar } from '../components/containers'
import { ChatPanel } from '../components/containers/ChatPanel'
import { primaryFromPathname, type PrimarySection } from '../lib/navigation'

export function WorkspaceLayout() {
  const location = useLocation()
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  const [secondaryPinned, setSecondaryPinned] = useState(true)
  const [secondaryHover, setSecondaryHover] = useState(false)
  const hoverClearTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

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
      setSecondaryHover(false)
      hoverClearTimer.current = null
    }, 220)
  }, [cancelHoverClear])

  const secondaryVisible = secondaryPinned

  const handleExplorerColumnEnter = useCallback(() => {
    if (!secondaryPinned) return
    cancelHoverClear()
    setSecondaryHover(true)
  }, [cancelHoverClear, secondaryPinned])

  const onPrimaryClick = useCallback(() => {
    setSecondaryPinned(true)
    cancelHoverClear()
  }, [cancelHoverClear])

  useEffect(() => () => cancelHoverClear(), [cancelHoverClear])

  return (
    <div className="flex h-dvh max-h-dvh flex-col overflow-hidden bg-[#0a0a0a] text-zinc-100">
      {/* Top bar */}
      <TopBar onMenuClick={() => setMobileNavOpen(true)} />

      <div className="flex min-h-0 min-w-0 flex-1">
        {/* Primary icon rail + Secondary nav — desktop */}
        <div
          className="relative hidden min-h-0 max-h-full md:flex"
          onMouseEnter={cancelHoverClear}
          onMouseLeave={scheduleHoverClear}
        >
          <div className="relative w-[52px] shrink-0 self-stretch min-h-0">
            <IconRail
              activePrimary={routePrimary}
              onPrimaryClick={onPrimaryClick}
              onToggleSecondary={() => setSecondaryPinned(!secondaryPinned)}
              secondaryVisible={secondaryVisible}
            />
          </div>
          {secondaryVisible && (
            <SecondaryNav primary={routePrimary} onPanelEnter={handleExplorerColumnEnter} />
          )}
        </div>

        {/* Main content */}
        <main className="min-h-0 min-w-0 flex-1 overflow-y-auto border-l border-zinc-800/60 bg-[#0a0a0a] px-3 py-5 sm:px-5 sm:py-6 lg:px-8">
          <div className="flex min-h-0 w-full min-w-0 max-w-4xl flex-col justify-start">
            <Outlet />
          </div>
        </main>

        {/* Chat panel — right side */}
        <div className="hidden min-h-0 lg:flex">
          <ChatPanel />
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
              <SecondaryNav
                primary={routePrimary}
                fullWidth
                onNavigate={() => setMobileNavOpen(false)}
              />
            </div>
          </div>
        </>
      )}
    </div>
  )
}
