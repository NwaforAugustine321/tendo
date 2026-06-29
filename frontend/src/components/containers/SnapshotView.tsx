import { Clock, AlertTriangle, CheckCircle2, MinusCircle, ArrowRight } from 'lucide-react'
import clsx from 'clsx'
import type { BusinessSnapshot, SnapshotStory, SnapshotRecommendation } from '../../lib/services/snapshot'

type Props = {
  snapshot: BusinessSnapshot | null
  loading?: boolean
  children?: React.ReactNode
}

const SENTIMENT_STYLES: Record<SnapshotStory['sentiment'], { border: string; badge: string; icon: typeof CheckCircle2 }> = {
  positive: { border: 'border-emerald-600/30', badge: 'bg-emerald-900/40 text-emerald-400', icon: CheckCircle2 },
  neutral: { border: 'border-zinc-700/50', badge: 'bg-zinc-800/60 text-zinc-400', icon: MinusCircle },
  attention_needed: { border: 'border-amber-600/30', badge: 'bg-amber-900/40 text-amber-400', icon: AlertTriangle },
}

const PRIORITY_STYLES: Record<SnapshotRecommendation['priority'], string> = {
  high: 'bg-red-900/40 text-red-400 border-red-700/40',
  medium: 'bg-amber-900/40 text-amber-400 border-amber-700/40',
  low: 'bg-zinc-800/60 text-zinc-400 border-zinc-700/40',
}

function StoryCard({ story }: { story: SnapshotStory }) {
  const style = SENTIMENT_STYLES[story.sentiment] || SENTIMENT_STYLES.neutral
  const Icon = style.icon

  return (
    <div
      className={clsx(
        'rounded-xl border bg-[#111111] p-3 transition-colors hover:bg-[#161616] w-[200px]',
        style.border
      )}
    >
      <div className="flex items-start justify-between gap-2 mb-1.5">
        <h3 className="text-[11px] font-semibold text-white leading-tight line-clamp-2">{story.title}</h3>
        <Icon size={12} className={clsx(style.badge.split(' ').pop(), 'shrink-0')} />
      </div>
      <p className="text-[10px] text-zinc-400 leading-relaxed line-clamp-3 mb-2">{story.narrative}</p>
      <span className={clsx('inline-flex items-center rounded-full px-2 py-0.5 text-[9px] font-medium', style.badge)}>
        {story.area}
      </span>
    </div>
  )
}

function RecommendationItem({ recommendation }: { recommendation: SnapshotRecommendation }) {
  const priorityStyle = PRIORITY_STYLES[recommendation.priority] || PRIORITY_STYLES.low

  return (
    <div className="flex items-start gap-2 rounded-lg border border-zinc-800/50 bg-[#111111] px-3 py-2">
      <ArrowRight size={12} className="text-emerald-500 mt-0.5 shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-[11px] text-white leading-snug">{recommendation.action}</p>
        <p className="text-[10px] text-zinc-500 mt-0.5">{recommendation.reason}</p>
      </div>
      <span className={clsx('inline-flex items-center rounded-full border px-1.5 py-0.5 text-[9px] font-medium shrink-0', priorityStyle)}>
        {recommendation.priority}
      </span>
    </div>
  )
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-8 px-6 text-center">
      <div className="w-10 h-10 rounded-full bg-zinc-800/60 border border-zinc-700/50 flex items-center justify-center mb-3">
        <Clock size={16} className="text-zinc-500" />
      </div>
      <p className="text-[11px] text-zinc-500 max-w-xs">
        Your business insights will appear here once enough data is collected.
      </p>
    </div>
  )
}

export function SnapshotView({ snapshot, loading, children }: Props) {
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-16">
        <div className="w-6 h-6 border-2 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin" />
        <p className="text-xs text-zinc-500 mt-3">Loading insights...</p>
      </div>
    )
  }

  if (!snapshot || (snapshot.stories.length === 0 && snapshot.recommendations.length === 0)) {
    return (
      <div className="flex flex-col items-center">
        {children && <div className="flex justify-center py-4">{children}</div>}
        <EmptyState />
      </div>
    )
  }

  // Split stories into positions around the hub
  const stories = snapshot.stories.slice(0, 5)
  const [top, ...rest] = stories
  const left = rest[0]
  const right = rest[1]
  const bottomLeft = rest[2]
  const bottomRight = rest[3]

  return (
    <div className="flex flex-col items-center gap-4 w-full max-w-[960px] mx-auto px-4 py-2">
      {/* Orbital layout: stories around the central hub */}
      <div className="grid grid-cols-[1fr_auto_1fr] grid-rows-[auto_1fr_auto] gap-[clamp(8px,1.5vw,16px)] w-full items-center justify-items-center">
        {/* Row 1: top story centered */}
        <div />
        <div>{top && <StoryCard story={top} />}</div>
        <div />

        {/* Row 2: left stories | center hub | right stories */}
        <div className="flex flex-col gap-3 justify-self-start">
          {left && <StoryCard story={left} />}
          {bottomLeft && <StoryCard story={bottomLeft} />}
        </div>

        <div className="relative flex items-center justify-center min-w-[240px] min-h-[240px]">
          {/* Decorative dots */}
          <div className="absolute -left-6 top-1/3 w-[6px] h-[6px] rounded-full bg-emerald-400 opacity-60" />
          <div className="absolute -right-6 top-1/3 w-[6px] h-[6px] rounded-full bg-emerald-400 opacity-60" />
          <div className="absolute -left-6 bottom-1/3 w-[6px] h-[6px] rounded-full bg-amber-400 opacity-60" />
          <div className="absolute -right-6 bottom-1/3 w-[6px] h-[6px] rounded-full bg-amber-400 opacity-60" />
          {children}
        </div>

        <div className="flex flex-col gap-3 justify-self-end">
          {right && <StoryCard story={right} />}
          {bottomRight && <StoryCard story={bottomRight} />}
        </div>

        {/* Row 3: empty (stories fill left/right) */}
        <div />
        <div />
        <div />
      </div>

      {/* Recommendations below the orbital layout */}
      {snapshot.recommendations.length > 0 && (
        <section className="w-full max-w-[600px]">
          <h2 className="text-[10px] font-semibold uppercase tracking-wider text-zinc-500 mb-2">
            Recommendations
          </h2>
          <div className="flex flex-col gap-2">
            {snapshot.recommendations.map((rec, idx) => (
              <RecommendationItem key={`${rec.priority}-${idx}`} recommendation={rec} />
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
