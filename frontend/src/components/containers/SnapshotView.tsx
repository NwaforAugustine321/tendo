import { useState, useEffect, useRef } from 'react'
import { AlertTriangle, CheckCircle2, MinusCircle, ArrowRight } from 'lucide-react'
import clsx from 'clsx'
import type { BusinessSnapshot, SnapshotStory, SnapshotRecommendation } from '../../lib/services/snapshot'

type Props = {
  snapshot: BusinessSnapshot | null
  loading?: boolean
}

const SENTIMENT_STYLES: Record<SnapshotStory['sentiment'], { border: string; badge: string; icon: typeof CheckCircle2; bg: string }> = {
  positive: { border: 'border-emerald-600/20', badge: 'bg-emerald-900/40 text-emerald-400', icon: CheckCircle2, bg: 'bg-emerald-950/20' },
  neutral: { border: 'border-zinc-700/40', badge: 'bg-zinc-800/60 text-zinc-400', icon: MinusCircle, bg: 'bg-zinc-900/30' },
  attention_needed: { border: 'border-amber-600/20', badge: 'bg-amber-900/40 text-amber-400', icon: AlertTriangle, bg: 'bg-amber-950/20' },
}

const PRIORITY_STYLES: Record<SnapshotRecommendation['priority'], string> = {
  high: 'text-red-400',
  medium: 'text-amber-400',
  low: 'text-zinc-400',
}

const ROTATE_INTERVAL = 8000

function HeroCard({ story }: { story: SnapshotStory }) {
  const style = SENTIMENT_STYLES[story.sentiment] || SENTIMENT_STYLES.neutral
  const Icon = style.icon

  return (
    <div className={clsx(
      'rounded-2xl border p-6 h-full flex flex-col justify-between transition-all duration-500 animate-[fadeIn_0.4s_ease-out]',
      style.border, style.bg
    )}>
      <div>
        <div className="flex items-center gap-2 mb-3">
          <Icon size={15} className={style.badge.split(' ').pop()} />
          <span className={clsx('text-[10px] font-medium rounded-full px-2.5 py-0.5', style.badge)}>{story.area}</span>
        </div>
        <h3 className="text-[17px] font-bold text-white leading-snug mb-3">{story.title}</h3>
        <p className="text-[13px] text-zinc-300 leading-relaxed">{story.narrative}</p>
      </div>
    </div>
  )
}

function SmallCard({ story, isActive, onClick }: { story: SnapshotStory; isActive: boolean; onClick: () => void }) {
  const style = SENTIMENT_STYLES[story.sentiment] || SENTIMENT_STYLES.neutral
  const Icon = style.icon

  return (
    <button
      type="button"
      onClick={onClick}
      className={clsx(
        'rounded-xl border p-3 min-w-[240px] max-w-[260px] flex-shrink-0 text-left transition-all duration-300',
        'hover:scale-[1.03]',
        isActive
          ? clsx(style.border, 'bg-[#141414] ring-1 ring-emerald-500/30')
          : 'border-zinc-800/30 bg-[#0c0c0c] opacity-70 hover:opacity-100'
      )}
    >
      <div className="flex items-center justify-between mb-1.5">
        <span className={clsx('text-[9px] font-medium rounded-full px-2 py-0.5', style.badge)}>{story.area}</span>
        <Icon size={11} className={style.badge.split(' ').pop()} />
      </div>
      <h3 className="text-[11px] font-semibold text-white leading-tight line-clamp-1 mb-1">{story.title}</h3>
      <p className="text-[10px] text-zinc-500 leading-relaxed line-clamp-2">{story.narrative}</p>
    </button>
  )
}

function RecommendationStrip({ recommendations }: { recommendations: SnapshotRecommendation[] }) {
  return (
    <div className="rounded-xl border border-zinc-800/30 bg-[#0a0a0a] p-4 flex flex-col gap-3 h-full">
      <h2 className="text-[10px] font-bold uppercase tracking-wider text-zinc-500">Actions</h2>
      {recommendations.map((rec, idx) => {
        const color = PRIORITY_STYLES[rec.priority] || PRIORITY_STYLES.low
        return (
          <div key={idx} className="flex items-start gap-2">
            <ArrowRight size={11} className="text-emerald-500 mt-0.5 shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-[11px] text-white leading-snug">{rec.action}</p>
              <p className="text-[10px] text-zinc-500 mt-0.5 line-clamp-1">{rec.reason}</p>
            </div>
            <span className={clsx('text-[9px] font-medium shrink-0', color)}>{rec.priority}</span>
          </div>
        )
      })}
    </div>
  )
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      {/* Animated icon */}
      <div className="relative mb-6">
        {/* Outer pulsing ring */}
        <div className="absolute inset-0 w-24 h-24 rounded-full border border-emerald-500/20 animate-ping" />
        {/* Middle ring */}
        <div className="absolute inset-2 w-20 h-20 rounded-full border border-emerald-500/10 animate-pulse" />
        {/* Center icon */}
        <div className="relative w-24 h-24 rounded-full bg-zinc-800/60 border border-zinc-700/40 flex items-center justify-center">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" className="text-emerald-500/70 animate-bounce" style={{ animationDuration: '2s' }}>
            <path d="M12 2L12 6M12 18L12 22M2 12H6M18 12H22" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            <circle cx="12" cy="12" r="4" stroke="currentColor" strokeWidth="1.5" />
            <path d="M12 8V12L14 14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>

      <h3 className="text-[14px] font-semibold text-zinc-300 mb-2">Gathering business intelligence</h3>
      <p className="text-[12px] text-zinc-500 max-w-[280px] leading-relaxed">
        How your bussines is doing today. Insights will appear here as it emerge.
      </p>
    </div>
  )
}

export function SnapshotView({ snapshot, loading }: Props) {
  const [activeIndex, setActiveIndex] = useState(0)
  const scrollRef = useRef<HTMLDivElement>(null)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const stories = snapshot?.stories || []

  // Auto-rotate
  useEffect(() => {
    if (stories.length <= 1) return
    timerRef.current = setInterval(() => {
      setActiveIndex((prev) => (prev + 1) % stories.length)
    }, ROTATE_INTERVAL)
    return () => { if (timerRef.current) clearInterval(timerRef.current) }
  }, [stories.length])

  // Scroll active card into view
  useEffect(() => {
    if (!scrollRef.current) return
    const cards = scrollRef.current.children
    if (cards[activeIndex]) {
      (cards[activeIndex] as HTMLElement).scrollIntoView({
        behavior: 'smooth',
        inline: 'center',
        block: 'nearest',
      })
    }
  }, [activeIndex])

  const handleCardClick = (idx: number) => {
    setActiveIndex(idx)
    // Reset auto-rotate timer
    if (timerRef.current) clearInterval(timerRef.current)
    timerRef.current = setInterval(() => {
      setActiveIndex((prev) => (prev + 1) % stories.length)
    }, ROTATE_INTERVAL)
  }

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-16">
        <div className="w-5 h-5 border-2 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin" />
        <p className="text-[11px] text-zinc-500 mt-3">Loading insights...</p>
      </div>
    )
  }

  const hasContent = snapshot && (stories.length > 0 || (snapshot.recommendations?.length || 0) > 0)

  if (!hasContent) {
    return <EmptyState />
  }

  const activeStory = stories[activeIndex]

  return (
    <div className="flex flex-col h-full overflow-y-auto gap-4 p-4">
      {/* Hero + Recommendations bento */}
      <div className="grid grid-cols-1 lg:grid-cols-[2fr_1fr] gap-3 w-full max-w-[900px] mx-auto min-h-[200px]">
        {/* Active story as hero */}
        {activeStory && <HeroCard story={activeStory} />}

        {/* Recommendations sidebar */}
        {snapshot.recommendations.length > 0 && (
          <RecommendationStrip recommendations={snapshot.recommendations} />
        )}
      </div>

      {/* Horizontal scrollable story cards */}
      {stories.length > 1 && (
        <div className="w-full max-w-[900px] mx-auto relative">
          <div
            ref={scrollRef}
            className="flex gap-3 overflow-x-auto pb-2 scrollbar-hide snap-x snap-mandatory"
            style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}
          >
            {stories.map((story, idx) => (
              <div key={idx} className="snap-center">
                <SmallCard
                  story={story}
                  isActive={idx === activeIndex}
                  onClick={() => handleCardClick(idx)}
                />
              </div>
            ))}
          </div>

          {/* Dot indicators */}
          <div className="flex justify-center gap-1.5 mt-2">
            {stories.map((_, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => handleCardClick(idx)}
                className={clsx(
                  'w-1.5 h-1.5 rounded-full transition-all',
                  idx === activeIndex ? 'bg-emerald-500 w-3' : 'bg-zinc-700 hover:bg-zinc-500'
                )}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
