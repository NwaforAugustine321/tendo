import { useState, useEffect, useRef, useCallback } from 'react'
import { Mic, X, ChevronLeft, ChevronRight } from 'lucide-react'
import clsx from 'clsx'

type InsightCard = {
  id: string
  insight: string
  area: string
  importance: number
  timestamp: string
  payload: Record<string, unknown>
}

const AREA_COLORS: Record<string, string> = {
  sales: 'bg-green-500',
  finance: 'bg-amber-500',
  operations: 'bg-blue-500',
  customers: 'bg-purple-500',
  general: 'bg-zinc-500',
  inventory: 'bg-cyan-500',
  hr: 'bg-pink-500',
  marketing: 'bg-orange-500',
}

const ALL_INSIGHTS: InsightCard[] = [
  { id: '1', insight: 'Your business profile has been established as a hybrid tech and retail operation based in Maryland. This foundational identity anchors all future business understanding.', area: 'general', importance: 0.7, timestamp: new Date(Date.now() - 1000 * 60 * 30).toISOString(), payload: { event_type: 'BusinessProfileUpdated' } },
  { id: '2', insight: 'Cash payments dominate your transaction pattern. 4 out of 5 recent sales were cash-based, suggesting your customer base prefers immediate payment methods.', area: 'sales', importance: 0.8, timestamp: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(), payload: { pattern: 'cash_dominant' } },
  { id: '3', insight: 'Morning shift (8-11am) accounts for 65% of daily revenue. Walk-in traffic peaks before 10am consistently over the past week.', area: 'operations', importance: 0.6, timestamp: new Date(Date.now() - 1000 * 60 * 60 * 5).toISOString(), payload: { peak_hours: '08:00-11:00' } },
  { id: '4', insight: 'Customer Amaka is a repeat buyer in the beauty category. Third purchase this week (₦5,000 cash).', area: 'customers', importance: 0.85, timestamp: new Date(Date.now() - 1000 * 60 * 60).toISOString(), payload: { pattern: 'repeat_customer' } },
  { id: '5', insight: 'Inventory of hair products is running low. Only 3 units remaining after this week\'s sales.', area: 'inventory', importance: 0.9, timestamp: new Date(Date.now() - 1000 * 60 * 45).toISOString(), payload: { alert: 'low_stock' } },
  { id: '6', insight: 'Revenue grew 12% compared to last week. Driven by increased walk-in traffic on Wednesday.', area: 'finance', importance: 0.75, timestamp: new Date(Date.now() - 1000 * 60 * 60 * 3).toISOString(), payload: { growth: 0.12 } },
  { id: '7', insight: 'Most popular product this week: "Shea Butter Hair Cream" with 8 units sold.', area: 'sales', importance: 0.65, timestamp: new Date(Date.now() - 1000 * 60 * 60 * 4).toISOString(), payload: { top_product: true } },
  { id: '8', insight: 'Two new customers onboarded today. Both from referrals — word of mouth is working.', area: 'marketing', importance: 0.7, timestamp: new Date(Date.now() - 1000 * 60 * 20).toISOString(), payload: { channel: 'referral' } },
  { id: '9', insight: 'Average transaction value increased to ₦4,200 from ₦3,500 last week.', area: 'finance', importance: 0.72, timestamp: new Date(Date.now() - 1000 * 60 * 60 * 6).toISOString(), payload: { metric: 'avg_transaction' } },
  { id: '10', insight: 'Staff member Bola has handled 70% of transactions today. Consider distributing workload.', area: 'operations', importance: 0.6, timestamp: new Date(Date.now() - 1000 * 60 * 90).toISOString(), payload: { workload: 'unbalanced' } },
]

const VISIBLE_CARDS = 6
const ROTATE_INTERVAL_MS = 5000

function formatRelativeTime(timestamp: string): string {
  const diff = Date.now() - new Date(timestamp).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  return `${Math.floor(hours / 24)}d ago`
}

function getOrbitPosition(index: number, total: number, radius: number): { x: number; y: number } {
  const angle = (index / total) * 2 * Math.PI - Math.PI / 2
  return { x: radius * Math.cos(angle), y: radius * Math.sin(angle) }
}

export function InsightsFeed() {
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [visible, setVisible] = useState(false)
  const [startIndex, setStartIndex] = useState(0)
  const [fadingOut, setFadingOut] = useState(false)
  const [isRecording, setIsRecording] = useState(false)
  const prefersReducedMotion = useRef(false)
  const rotateTimer = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    prefersReducedMotion.current = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const timer = setTimeout(() => setVisible(true), 50)
    return () => clearTimeout(timer)
  }, [])

  useEffect(() => {
    const handleRecordingState = (e: Event) => {
      setIsRecording((e as CustomEvent).detail?.recording ?? false)
    }
    window.addEventListener('tendo:recording-state', handleRecordingState)
    return () => window.removeEventListener('tendo:recording-state', handleRecordingState)
  }, [])

  const handleMicClick = useCallback(() => {
    window.dispatchEvent(new CustomEvent('tendo:voice-toggle'))
    setIsRecording((prev) => !prev)
  }, [])

  const rotate = useCallback(() => {
    if (ALL_INSIGHTS.length <= VISIBLE_CARDS) return
    setFadingOut(true)
    setTimeout(() => {
      setStartIndex((prev) => (prev + 1) % ALL_INSIGHTS.length)
      setFadingOut(false)
    }, 400)
  }, [])

  useEffect(() => {
    if (prefersReducedMotion.current) return
    rotateTimer.current = setInterval(rotate, ROTATE_INTERVAL_MS)
    return () => { if (rotateTimer.current) clearInterval(rotateTimer.current) }
  }, [rotate])

  const getVisibleInsights = (): InsightCard[] => {
    const result: InsightCard[] = []
    for (let i = 0; i < VISIBLE_CARDS; i++) {
      result.push(ALL_INSIGHTS[(startIndex + i) % ALL_INSIGHTS.length])
    }
    return result
  }

  const navigateInsight = useCallback((dir: number) => {
    if (!expandedId) return
    const currentIdx = ALL_INSIGHTS.findIndex((i) => i.id === expandedId)
    const nextIdx = (currentIdx + dir + ALL_INSIGHTS.length) % ALL_INSIGHTS.length
    setExpandedId(ALL_INSIGHTS[nextIdx].id)
  }, [expandedId])

  const insights = getVisibleInsights()
  const hasInsights = ALL_INSIGHTS.length > 0
  const orbitRadius = typeof window !== 'undefined' && window.innerWidth < 640 ? 180 : 300
  const selectedInsight = expandedId ? ALL_INSIGHTS.find((i) => i.id === expandedId) : null

  return (
    <div className="relative flex h-full w-full items-center justify-center overflow-hidden">
      {/* Orbit cards */}
      {hasInsights && insights.map((card, index) => {
        const { x, y } = getOrbitPosition(index, insights.length, orbitRadius)
        const areaColor = AREA_COLORS[card.area] || 'bg-zinc-500'

        return (
          <div
            key={`${card.id}-${startIndex}`}
            className={clsx(
              'absolute z-10 w-[170px] cursor-pointer rounded-xl border bg-[#0f0f0f] p-3 transition-all duration-500',
              expandedId === card.id ? 'border-[#3ecf8e]/40' : 'border-white/5 hover:scale-105 hover:border-white/15',
              fadingOut ? 'opacity-0 scale-95' : 'opacity-100 scale-100',
              !visible && 'opacity-0'
            )}
            style={{
              left: '50%',
              top: '50%',
              transform: `translate(-50%, -50%) translate(${x}px, ${y}px)`,
              transitionDelay: !prefersReducedMotion.current ? `${index * 60}ms` : '0ms',
            }}
            onClick={() => setExpandedId(expandedId === card.id ? null : card.id)}
          >
            <div className="mb-1.5 flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <span className={clsx('h-2 w-2 rounded-full', areaColor)} />
                <span className="text-[10px] font-medium capitalize text-zinc-400">{card.area}</span>
              </div>
              <span className="text-[9px] text-zinc-600">{formatRelativeTime(card.timestamp)}</span>
            </div>
            <p className="text-xs leading-relaxed text-zinc-300 line-clamp-2">{card.insight}</p>
          </div>
        )
      })}

      {/* Center mic circle */}
      <div
        className={clsx(
          'relative z-20 flex h-[180px] w-[180px] cursor-pointer flex-col items-center justify-center rounded-full',
          'border-2 bg-[#111111]',
          'shadow-[0_0_40px_rgba(62,207,142,0.08),0_0_80px_rgba(62,207,142,0.04)]',
          'transition-all duration-300',
          isRecording
            ? 'border-red-400 shadow-[0_0_40px_rgba(248,113,113,0.15)]'
            : 'border-[#3ecf8e]/30 hover:border-[#3ecf8e]/50 hover:shadow-[0_0_50px_rgba(62,207,142,0.12)]',
          !hasInsights && !isRecording && 'animate-pulse',
          visible ? 'scale-100 opacity-100' : 'scale-90 opacity-0'
        )}
        onClick={handleMicClick}
      >
        {isRecording && <span className="absolute inset-0 animate-ping rounded-full border border-red-400/20" />}
        <div className={clsx('mb-3 flex h-14 w-14 items-center justify-center rounded-full transition-colors', isRecording ? 'bg-red-500/10 text-red-400' : 'bg-[#3ecf8e]/10 text-[#3ecf8e]')}>
          <Mic size={32} />
        </div>
        <p className={clsx('max-w-[140px] text-center text-[11px] leading-tight', isRecording ? 'text-red-400' : 'text-zinc-400')}>
          {isRecording ? 'Listening... tap to stop' : 'Hey! Jay is here, use the mic or text me'}
        </p>
      </div>

      {/* Center modal with carousel navigation */}
      {selectedInsight && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setExpandedId(null)}>
          <div
            className="w-[720px] max-w-[92%] h-[75%] flex flex-col rounded-2xl border border-dashed border-zinc-600 bg-[#0a0a0a] shadow-2xl animate-[fadeInUp_0.2s_ease-out_forwards] relative"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Left slide button */}
            <button type="button" onClick={() => navigateInsight(-1)} className="absolute left-0 top-1/2 -translate-x-1/2 -translate-y-1/2 z-10 flex h-10 w-10 items-center justify-center rounded-full border border-zinc-700 bg-[#1a1a1a] text-zinc-400 hover:border-zinc-500 hover:text-zinc-200 transition-colors" title="Previous">
              <ChevronLeft size={20} />
            </button>

            {/* Right slide button */}
            <button type="button" onClick={() => navigateInsight(1)} className="absolute right-0 top-1/2 translate-x-1/2 -translate-y-1/2 z-10 flex h-10 w-10 items-center justify-center rounded-full border border-zinc-700 bg-[#1a1a1a] text-zinc-400 hover:border-zinc-500 hover:text-zinc-200 transition-colors" title="Next">
              <ChevronRight size={20} />
            </button>

            {/* Toolbar */}
            <div className="flex items-center justify-between border-b border-zinc-800 px-6 py-3">
              <div className="flex items-center gap-3">
                <span className={clsx('h-3 w-3 rounded-full', AREA_COLORS[selectedInsight.area] || 'bg-zinc-500')} />
                <span className="text-sm font-medium capitalize text-zinc-200">{selectedInsight.area}</span>
                <span className="text-xs text-zinc-500">{formatRelativeTime(selectedInsight.timestamp)}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[11px] text-zinc-500">
                  {ALL_INSIGHTS.findIndex((i) => i.id === selectedInsight.id) + 1} / {ALL_INSIGHTS.length}
                </span>
                <button type="button" onClick={() => setExpandedId(null)} className="rounded p-1.5 text-zinc-500 hover:bg-white/5 hover:text-zinc-300" title="Close">
                  <X size={16} />
                </button>
              </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-8">
              <p className="text-lg leading-relaxed text-zinc-200">{selectedInsight.insight}</p>
            </div>

            {/* Footer */}
            <div className="border-t border-zinc-800 px-6 py-3 flex items-center gap-3 text-xs text-zinc-500">
              <span>Importance: {Math.round(selectedInsight.importance * 100)}%</span>
              {selectedInsight.payload && Object.keys(selectedInsight.payload).length > 0 && (
                <span className="text-zinc-600">| {Object.entries(selectedInsight.payload).map(([k, v]) => `${k}: ${v}`).join(', ')}</span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Empty state */}
      {!hasInsights && visible && (
        <p className="absolute bottom-8 text-center text-xs text-zinc-600">
          Your insights will orbit here as Tendo learns about your business
        </p>
      )}
    </div>
  )
}
