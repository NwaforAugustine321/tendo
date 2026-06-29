import { useState, useEffect } from 'react'
import { useBusinessStore } from '../../store/business'
import { useWorkspaceStore } from '../../store/workspace'
import { GreetingHeader, CentralHub, SnapshotView, StatsBar } from '../../components/containers'
import { TendoAILabel } from '../../components/atoms'
import { getSnapshot } from '../../lib/services/snapshot'
import { getInsightStats } from '../../lib/services/insights'
import type { DashboardStats, TimeRange } from '../../lib/workspace/dashboard-types'
import type { BusinessSnapshot } from '../../lib/services/snapshot'

export function Dashboard() {
  const { currentProfile } = useBusinessStore()
  const { setDashboardSidebarVisible, setDashboardChatVisible } = useWorkspaceStore()

  const [timeRange, setTimeRange] = useState<TimeRange>('today')
  const [snapshot, setSnapshot] = useState<BusinessSnapshot | null>(null)
  const [snapshotLoading, setSnapshotLoading] = useState(true)
  const [stats, setStats] = useState<DashboardStats | null>(null)

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

  // Fetch stats
  useEffect(() => {
    if (!currentProfile?.id) return
    getInsightStats(currentProfile.id, timeRange)
      .then((data) => {
        if (data) setStats(data)
      })
      .catch(() => {})
  }, [currentProfile?.id, timeRange])

  const handleMicClick = () => {
    // Dispatch voice toggle event — picked up by the Conversation component
    window.dispatchEvent(new CustomEvent('tendo:voice-toggle'))
    // Show the chat panel so the user sees the conversation
    setDashboardChatVisible(true)
  }

  return (
    <div className="relative flex flex-col h-full overflow-hidden bg-[#0a0a0a]">
      {/* Greeting header */}
      <GreetingHeader
        name={currentProfile?.name || 'there'}
        timeRange={timeRange}
        onTimeRangeChange={setTimeRange}
      />

      {/* Snapshot view with central hub — scrollable area */}
      <div className="flex-1 overflow-y-auto relative">
        <SnapshotView snapshot={snapshot} loading={snapshotLoading}>
          <CentralHub onMicClick={handleMicClick} />
        </SnapshotView>
      </div>

      {/* Stats bar at bottom — always visible */}
      <StatsBar stats={stats} />

      {/* Tendo AI label — floating bottom-right */}
      <TendoAILabel />
    </div>
  )
}
