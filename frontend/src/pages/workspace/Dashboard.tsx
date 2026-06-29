import { useState, useEffect } from 'react'
import { useBusinessStore } from '../../store/business'
import { useWorkspaceStore } from '../../store/workspace'
import { GreetingHeader, CentralHub, SnapshotView } from '../../components/containers'
import { TendoAILabel } from '../../components/atoms'
import { getSnapshot } from '../../lib/services/snapshot'
import type { BusinessSnapshot } from '../../lib/services/snapshot'

export function Dashboard() {
  const { currentProfile } = useBusinessStore()
  const { setDashboardSidebarVisible, setDashboardChatVisible } = useWorkspaceStore()

  const [snapshot, setSnapshot] = useState<BusinessSnapshot | null>(null)
  const [snapshotLoading, setSnapshotLoading] = useState(true)

  // Hide sidebar and chat on mount
  useEffect(() => {
    setDashboardSidebarVisible(false)
    setDashboardChatVisible(false)
  }, [setDashboardSidebarVisible, setDashboardChatVisible])

  // Fetch snapshot on mount
  useEffect(() => {
    if (!currentProfile?.id) {
      setSnapshotLoading(false)
      return
    }
    setSnapshotLoading(true)
    getSnapshot(currentProfile.id)
      .then((data) => setSnapshot(data))
      .catch(() => setSnapshot(null))
      .finally(() => setSnapshotLoading(false))
  }, [currentProfile?.id])

  const handleMicClick = () => {
    window.dispatchEvent(new CustomEvent('tendo:voice-toggle'))
    setDashboardChatVisible(true)
  }

  return (
    <div className="relative flex flex-col h-full overflow-hidden bg-[#0a0a0a]">
      {/* Greeting header */}
      <GreetingHeader
        name={currentProfile?.name || 'there'}
        recommendations={snapshot?.recommendations || []}
      />

      {/* Snapshot view — scrollable area */}
      <div className="flex-1 overflow-y-auto relative pb-20">
        <SnapshotView snapshot={snapshot} loading={snapshotLoading} />
      </div>

      {/* Fixed compact mic button — bottom center */}
      <div className="fixed bottom-5 left-1/2 -translate-x-1/2 z-30 flex items-center gap-2 rounded-full bg-[#111111] border border-emerald-500/30 shadow-[0_0_20px_rgba(16,185,129,0.12)] px-4 py-2 cursor-pointer hover:border-emerald-500/50 transition-all" onClick={handleMicClick}>
        <CentralHub onMicClick={handleMicClick} compact />
        <span className="text-[12px] font-medium text-white">Ask Tendo</span>
      </div>

      {/* Tendo AI label */}
      <TendoAILabel />
    </div>
  )
}
