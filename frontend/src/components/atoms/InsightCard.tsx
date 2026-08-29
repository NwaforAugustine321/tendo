import clsx from 'clsx'
import { ChevronRight } from 'lucide-react'
import type { DashboardInsightCard } from '../../lib/workspace/dashboard-types'
import { getStatusBadgeColor } from '../../lib/workspace/dashboard-utils'

type Props = {
  card: DashboardInsightCard
  onViewDetails?: () => void
}

export function InsightCard({ card, onViewDetails }: Props) {
  const Icon = card.icon
  const badgeClasses = getStatusBadgeColor(card.status)
  const statusLabel = card.status === 'needs-attention'
    ? 'Needs attention'
    : card.status.charAt(0).toUpperCase() + card.status.slice(1)

  return (
    <div className="w-[clamp(200px,22vw,250px)] bg-zinc-900/90 border border-zinc-800/70 rounded-xl p-4 flex flex-col gap-2.5 backdrop-blur-sm">
      {/* Header: icon + category + status badge */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <Icon size={14} className="text-zinc-400" />
          <span className="text-[11px] font-medium text-zinc-300">{card.categoryName}</span>
        </div>
        <span
          className={clsx(
            'rounded-full border px-2 py-0.5 text-[9px] font-medium',
            badgeClasses
          )}
        >
          {statusLabel}
        </span>
      </div>

      {/* Summary */}
      <p className="text-[13px] text-zinc-100 leading-snug font-medium">
        {card.summary}
      </p>

      {/* Metadata */}
      <div className="flex items-center justify-between">
        <span className="text-[10px] text-zinc-500">{card.metadata}</span>
        <span className="text-[10px] text-zinc-600">{card.updatedAt}</span>
      </div>

      {/* View details link */}
      {onViewDetails && (
        <button
          type="button"
          onClick={onViewDetails}
          className="flex items-center justify-between pt-2 border-t border-zinc-800/50 text-[11px] text-zinc-400 hover:text-zinc-200 transition-colors"
        >
          <span>View details</span>
          <ChevronRight size={12} />
        </button>
      )}
    </div>
  )
}
