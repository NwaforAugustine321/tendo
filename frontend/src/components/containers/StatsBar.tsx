import { ArrowUpDown, DollarSign, Users, ShoppingBag } from 'lucide-react'
import type { DashboardStats } from '../../lib/workspace/dashboard-types'
import { StatItem } from '../atoms'

type Props = {
  stats: DashboardStats | null
}

export function StatsBar({ stats }: Props) {
  return (
    <div className="flex justify-center px-6 py-3 bg-[#0a0a0a]">
      <div className="flex items-center gap-6 rounded-xl border border-zinc-800/60 bg-[#111111] px-6 py-3">
        <StatItem
          label="Revenue today"
          icon={DollarSign}
          value={stats ? `₦${stats.revenue.current.toLocaleString()}` : '--'}
          changePercent={stats?.revenue.changePercent}
        />
        <div className="w-px h-8 bg-zinc-800/60" />
        <StatItem
          label="Transactions"
          icon={ArrowUpDown}
          value={stats ? stats.transactions.current : '--'}
          changePercent={stats?.transactions.changePercent}
        />
        <div className="w-px h-8 bg-zinc-800/60" />
        <StatItem
          label="Top category"
          icon={ShoppingBag}
          value={stats ? stats.topCategory.name : '--'}
          changePercent={stats ? stats.topCategory.percentage : undefined}
        />
        <div className="w-px h-8 bg-zinc-800/60" />
        <StatItem
          label="New customers"
          icon={Users}
          value={stats ? stats.newCustomers.current : '--'}
          changePercent={stats?.newCustomers.changePercent}
        />
      </div>
    </div>
  )
}
