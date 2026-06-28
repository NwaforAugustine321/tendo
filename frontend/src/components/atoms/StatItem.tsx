import clsx from 'clsx'
import type { LucideIcon } from 'lucide-react'
import { getChangeIndicatorColor } from '../../lib/workspace/dashboard-utils'

type Props = {
  label: string
  value: string | number
  changePercent?: number
  icon?: LucideIcon
}

export function StatItem({ label, value, changePercent, icon: Icon }: Props) {
  const changeColor = changePercent !== undefined ? getChangeIndicatorColor(changePercent) : ''
  const arrow = changePercent !== undefined && changePercent > 0
    ? '↑'
    : changePercent !== undefined && changePercent < 0
      ? '↓'
      : ''

  return (
    <div className="flex flex-col gap-0.5">
      <div className="flex items-center gap-1">
        {Icon && <Icon size={12} className="text-zinc-500" />}
        <span className="text-[10px] text-zinc-500 uppercase tracking-wide">{label}</span>
      </div>
      <div className="flex items-center gap-1.5">
        <span className="text-lg font-semibold text-white">{value}</span>
        {changePercent !== undefined && changePercent !== 0 && (
          <span className={clsx('text-xs font-medium', changeColor)}>
            {arrow}{Math.abs(changePercent)}%
          </span>
        )}
      </div>
    </div>
  )
}
