import { useState, useEffect } from 'react'
import { useBusinessStore } from '../../store/business'
import { useWorkspaceStore } from '../../store/workspace'
import { GreetingHeader, CentralHub, InsightCardRing, StatsBar } from '../../components/containers'
import { TendoAILabel } from '../../components/atoms'
import { getInsights, getInsightStats } from '../../lib/services/insights'
import { deriveStatus } from '../../lib/workspace/dashboard-utils'
import type { DashboardInsightCard, DashboardStats, TimeRange, BusinessInsight, InsightArea } from '../../lib/workspace/dashboard-types'
import { TrendingUp, Users, Package, DollarSign, Settings, BarChart3, Star } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

const AREA_ICON_MAP: Record<string, LucideIcon> = {
  sales: TrendingUp,
  finance: DollarSign,
  operations: Settings,
  customers: Users,
  inventory: Package,
  general: Star,
}

const AREA_LABEL_MAP: Record<string, string> = {
  sales: 'Sales',
  finance: 'Finance',
  operations: 'Operations',
  customers: 'Customers',
  inventory: 'Inventory',
  general: 'General',
}

// Dummy data matching the reference design
const DUMMY_CARDS: DashboardInsightCard[] = [
  {
    id: '1',
    area: 'finance' as InsightArea,
    icon: DollarSign,
    categoryName: 'Finance',
    status: 'growing',
    summary: 'Average transaction value increased by 18%',
    metadata: '↑ vs yesterday',
    updatedAt: 'Updated 2h ago',
    rawInsight: {} as BusinessInsight,
  },
  {
    id: '2',
    area: 'customers' as InsightArea,
    icon: Users,
    categoryName: 'Customers',
    status: 'growing',
    summary: 'Customer Amaka is a repeat buyer in the last 3 weeks',
    metadata: '★ High value customer',
    updatedAt: 'Updated 1h ago',
    rawInsight: {} as BusinessInsight,
  },
  {
    id: '3',
    area: 'operations' as InsightArea,
    icon: Settings,
    categoryName: 'Operations',
    status: 'needs-attention',
    summary: 'Staff member Bola has handled 70% of tasks this week',
    metadata: '● High workload',
    updatedAt: 'Updated 2h ago',
    rawInsight: {} as BusinessInsight,
  },
  {
    id: '4',
    area: 'inventory' as InsightArea,
    icon: Settings,
    categoryName: 'Operations',
    status: 'stable',
    summary: 'Morning shift (8-11am) accounts for 65% of productivity',
    metadata: '↑ Better than yesterday',
    updatedAt: 'Updated 5h ago',
    rawInsight: {} as BusinessInsight,
  },
  {
    id: '5',
    area: 'sales' as InsightArea,
    icon: TrendingUp,
    categoryName: 'Sales',
    status: 'growing',
    summary: 'Cash payments dominate your transaction pattern (78%)',
    metadata: '★ Consistent trend',
    updatedAt: 'Updated 2h ago',
    rawInsight: {} as BusinessInsight,
  },
  {
    id: '6',
    area: 'general' as InsightArea,
    icon: Star,
    categoryName: 'General',
    status: 'stable',
    summary: 'Your business profile has been established as a Retail Store',
    metadata: '● All systems active',
    updatedAt: 'Updated 1h ago',
    rawInsight: {} as BusinessInsight,
  },
]

const DUMMY_STATS: DashboardStats = {
  revenue: { current: 245600, changePercent: 12 },
  transactions: { current: 48, changePercent: 8 },
  topCategory: { name: 'Groceries', percentage: 42 },
  newCustomers: { current: 5, changePercent: 2 },
}

function mapInsightToCard(insight: BusinessInsight): DashboardInsightCard {
  return {
    id: insight.id,
    area: insight.area,
    icon: AREA_ICON_MAP[insight.area] || BarChart3,
    categoryName: AREA_LABEL_MAP[insight.area] || 'General',
    status: deriveStatus(insight),
    summary: insight.insight,
    metadata: insight.source_agent,
    updatedAt: insight.created_at,
    rawInsight: insight,
  }
}

export function Dashboard() {
  const { currentProfile } = useBusinessStore()
  const { setDashboardSidebarVisible, setDashboardChatVisible } = useWorkspaceStore()

  const [timeRange, setTimeRange] = useState<TimeRange>('today')
  const [cards, setCards] = useState<DashboardInsightCard[]>(DUMMY_CARDS)
  const [stats, setStats] = useState<DashboardStats | null>(DUMMY_STATS)

  // Hide sidebar and chat on mount
  useEffect(() => {
    setDashboardSidebarVisible(false)
    setDashboardChatVisible(false)
  }, [setDashboardSidebarVisible, setDashboardChatVisible])

  // Try to fetch real insights — fallback to dummy data
  useEffect(() => {
    if (!currentProfile?.id) return
    getInsights(currentProfile.id, 6)
      .then((insights) => {
        if (insights.length > 0) {
          setCards(insights.map(mapInsightToCard))
        }
      })
      .catch(() => {})
  }, [currentProfile?.id])

  // Try to fetch real stats — fallback to dummy data
  useEffect(() => {
    if (!currentProfile?.id) return
    getInsightStats(currentProfile.id, timeRange)
      .then((data) => {
        if (data) setStats(data)
      })
      .catch(() => {})
  }, [currentProfile?.id, timeRange])

  const handleMicClick = () => {
    console.log('[Dashboard] Mic clicked')
  }

  const handleViewDetails = (id: string) => {
    console.log('[Dashboard] View details:', id)
  }

  return (
    <div className="relative flex flex-col h-full overflow-hidden bg-[#0a0a0a]">
      {/* Greeting header */}
      <GreetingHeader
        name={currentProfile?.name || 'there'}
        timeRange={timeRange}
        onTimeRangeChange={setTimeRange}
      />

      {/* Insight card ring with central hub — scrollable area */}
      <div className="flex-1 overflow-y-auto relative">
        <InsightCardRing cards={cards} onViewDetails={handleViewDetails}>
          <CentralHub onMicClick={handleMicClick} />
        </InsightCardRing>
      </div>

      {/* Stats bar at bottom — always visible, not full width */}
      <StatsBar stats={stats} />

      {/* Tendo AI label — floating bottom-right (card style) */}
      <TendoAILabel />
    </div>
  )
}
