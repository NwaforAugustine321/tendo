import type { DashboardInsightCard } from '../../lib/workspace/dashboard-types'
import { InsightCard } from '../atoms'

type Props = {
  cards: DashboardInsightCard[]
  onViewDetails?: (id: string) => void
  children?: React.ReactNode
}

export function InsightCardRing({ cards, onViewDetails, children }: Props) {
  // Take max 5 cards: top, left, right, bottom-left, bottom
  const [top, left, right, bottomLeft, bottom] = cards.slice(0, 5)

  return (
    <div className="grid grid-cols-[1fr_auto_1fr] grid-rows-[auto_1fr_auto] gap-[clamp(8px,1.5vw,20px)] w-full max-w-[900px] mx-auto items-center justify-items-center py-2 px-2">
      {/* Row 1: top card centered */}
      <div />
      <div>
        {top && (
          <InsightCard card={top} onViewDetails={onViewDetails ? () => onViewDetails(top.id) : undefined} />
        )}
      </div>
      <div />

      {/* Row 2: left card | center hub | right card */}
      <div className="flex flex-col gap-4 justify-self-start">
        {left && (
          <InsightCard card={left} onViewDetails={onViewDetails ? () => onViewDetails(left.id) : undefined} />
        )}
        {bottomLeft && (
          <InsightCard card={bottomLeft} onViewDetails={onViewDetails ? () => onViewDetails(bottomLeft.id) : undefined} />
        )}
      </div>

      <div className="relative flex items-center justify-center min-w-[240px] min-h-[240px]">
        {/* Decorative dots */}
        <div className="absolute -left-8 top-1/3 w-[7px] h-[7px] rounded-full bg-violet-400 opacity-80" />
        <div className="absolute -right-8 top-1/3 w-[7px] h-[7px] rounded-full bg-sky-400 opacity-80" />
        <div className="absolute -left-8 bottom-1/3 w-[7px] h-[7px] rounded-full bg-sky-400 opacity-80" />
        <div className="absolute -right-8 bottom-1/3 w-[7px] h-[7px] rounded-full bg-amber-400 opacity-80" />
        <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-4 w-[7px] h-[7px] rounded-full bg-amber-400 opacity-80" />
        <div className="absolute bottom-0 left-1/2 -translate-x-1/2 translate-y-4 w-[7px] h-[7px] rounded-full bg-zinc-500 opacity-80" />
        {children}
      </div>

      <div className="flex flex-col gap-4 justify-self-end">
        {right && (
          <InsightCard card={right} onViewDetails={onViewDetails ? () => onViewDetails(right.id) : undefined} />
        )}
      </div>

      {/* Row 3: bottom card centered */}
      <div />
      <div>
        {bottom && (
          <InsightCard card={bottom} onViewDetails={onViewDetails ? () => onViewDetails(bottom.id) : undefined} />
        )}
      </div>
      <div />
    </div>
  )
}
