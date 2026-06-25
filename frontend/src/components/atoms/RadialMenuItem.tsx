import type { ReactNode } from 'react'
import clsx from 'clsx'

type Props = {
  icon: ReactNode
  label: string
  angle: number
  radius: number
  onClick: () => void
  index: number
  total: number
  /** Opacity from 0 to 1, controls visibility based on arc position */
  arcOpacity?: number
  /** Whether the item is within the visible arc */
  arcVisible?: boolean
}

export function RadialMenuItem({
  icon,
  label,
  angle,
  radius,
  onClick,
  index,
  total,
  arcOpacity = 1,
  arcVisible = true,
}: Props) {
  const radians = (angle * Math.PI) / 180
  const x = Math.cos(radians) * radius
  const y = Math.sin(radians) * radius

  if (!arcVisible) return null

  return (
    <button
      type="button"
      role="menuitem"
      aria-label={label}
      aria-posinset={index + 1}
      aria-setsize={total}
      onClick={onClick}
      className={clsx(
        'group absolute flex min-h-[44px] min-w-[44px] items-center gap-3',
        'rounded-lg p-2 transition-all duration-200 ease-out',
        'hover:scale-110',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3ecf8e]/60'
      )}
      style={{
        transform: `translate(${x}px, ${y}px) translate(-50%, -50%)`,
        opacity: arcOpacity,
        pointerEvents: arcOpacity < 0.3 ? 'none' : 'auto',
      }}
    >
      {/* Label on left side of icon */}
      <span className="whitespace-nowrap text-[11px] font-medium text-zinc-400 group-hover:text-white transition-colors">
        {label}
      </span>
      {/* Icon circle */}
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#1a1a1a] border border-white/10 text-[#3ecf8e] shadow-md group-hover:border-[#3ecf8e]/40 transition-colors">
        {icon}
      </span>
    </button>
  )
}
