import { useState, useEffect, useRef } from 'react'
import { ChevronRight, MessageSquare } from 'lucide-react'
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

const FILTER_OPTIONS = ['All', 'Sales', 'Finance', 'Operations', 'Customers', 'General']

const MOCK_INSIGHTS: InsightCard[] = [
  {
    id: '1',
    insight: 'Your business profile has been established as a hybrid tech and retail operation based in Maryland. This foundational identity anchors all future business understanding.',
    area: 'general',
    importance: 0.7,
    timestamp: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
    payload: { event_type: 'BusinessProfileUpdated', fields_changed: 'name, phone, location' },
  },
  {
    id: '2',
    insight: 'Cash payments dominate your transaction pattern. 4 out of 5 recent sales were cash-based, suggesting your customer base prefers immediate payment methods.',
    area: 'sales',
    importance: 0.8,
    timestamp: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(),
    payload: { evidence: ['4/5 transactions cash', 'No transfer payments this week'], pattern: 'cash_dominant' },
  },
  {
    id: '3',
    insight: 'Morning shift (8-11am) accounts for 65% of daily revenue. Walk-in traffic peaks before 10am consistently over the past week.',
    area: 'operations',
    importance: 0.6,
    timestamp: new Date(Date.now() - 1000 * 60 * 60 * 5).toISOString(),
    payload: { peak_hours: '08:00-11:00', revenue_share: 0.65 },
  },
]

function formatRelativeTime(timestamp: string): string {
  const diff = Date.now() - new Date(timestamp).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

function ImportanceDots({ value }: { value: number }) {
  const filled = Math.round(value * 4)
  return (
    <div className="flex items-center gap-0.5">
      {[0, 1, 2, 3].map((i) => (
        <span
          key={i}
          className={clsx(
            'h-1.5 w-1.5 rounded-full',
            i < filled ? 'bg-[#3ecf8e]' : 'bg-zinc-700'
          )}
        />
      ))}
    </div>
  )
}

export function InsightsFeed() {
  const [filter, setFilter] = useState('All')
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [visible, setVisible] = useState(false)
  const prefersReducedMotion = useRef(false)

  useEffect(() => {
    prefersReducedMotion.current = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    setVisible(true)
  }, [])

  const filtered = filter === 'All'
    ? MOCK_INSIGHTS
    : MOCK_INSIGHTS.filter((i) => i.area.toLowerCase() === filter.toLowerCase())

  return (
    <div className="flex h-full flex-col">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-base font-semibold text-zinc-200">Business Insights</h2>
      </div>

      <div className="mb-4 flex flex-wrap gap-2">
        {FILTER_OPTIONS.map((opt) => (
          <button
            key={opt}
            type="button"
            onClick={() => setFilter(opt)}
            className={clsx(
              'rounded-full px-3 py-1 text-xs font-medium transition-colors',
              filter === opt
                ? 'bg-[#3ecf8e]/20 text-[#3ecf8e] border border-[#3ecf8e]/40'
                : 'bg-zinc-800/50 text-zinc-400 border border-transparent hover:bg-zinc-800 hover:text-zinc-300'
            )}
          >
            {opt}
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <div className="flex flex-1 items-center justify-center">
          <p className="text-sm text-zinc-500">Your business insights will appear here as Tendo learns about your business</p>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto">
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            {filtered.map((card, index) => {
              const isExpanded = expandedId === card.id
              const areaColor = AREA_COLORS[card.area] || 'bg-zinc-500'
              const evidence = Array.isArray(card.payload?.evidence)
                ? (card.payload.evidence as string[])
                : []

              return (
                <div
                  key={card.id}
                  onClick={() => setExpandedId(isExpanded ? null : card.id)}
                  className={clsx(
                    'cursor-pointer rounded-xl border border-white/5 bg-[#0f0f0f] p-4 transition-all duration-200',
                    'hover:border-white/10 hover:bg-[#141414]',
                    isExpanded && 'border-[#3ecf8e]/20 bg-[#111]',
                    visible && !prefersReducedMotion.current && 'animate-[fadeInUp_0.4s_ease-out_forwards]',
                    !visible && 'opacity-0'
                  )}
                  style={
                    !prefersReducedMotion.current
                      ? { animationDelay: `${index * 100}ms`, opacity: 0 }
                      : undefined
                  }
                >
                  <div className="mb-2 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className={clsx('h-2 w-2 rounded-full', areaColor)} />
                      <span className="text-xs font-medium capitalize text-zinc-400">{card.area}</span>
                    </div>
                    <span className="text-[10px] text-zinc-600">{formatRelativeTime(card.timestamp)}</span>
                  </div>

                  <p className="mb-3 text-sm leading-relaxed text-zinc-300">{card.insight}</p>

                  <div
                    className={clsx(
                      'overflow-hidden transition-[max-height,opacity] duration-200',
                      isExpanded ? 'max-h-[300px] opacity-100' : 'max-h-0 opacity-0'
                    )}
                  >
                    {evidence.length > 0 && (
                      <div className="mb-3 rounded-lg bg-zinc-900/50 p-2.5">
                        <p className="mb-1 text-[10px] uppercase tracking-wide text-zinc-500">Evidence</p>
                        <ul className="space-y-0.5">
                          {evidence.map((e, i) => (
                            <li key={i} className="flex items-start gap-1.5 text-xs text-zinc-400">
                              <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-zinc-600" />
                              {e}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation() }}
                      className="flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium text-[#3ecf8e] transition-colors hover:bg-[#3ecf8e]/10"
                    >
                      <MessageSquare size={12} />
                      Ask about this
                      <ChevronRight size={10} />
                    </button>
                  </div>

                  <div className="flex items-center justify-between pt-1">
                    <ImportanceDots value={card.importance} />
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
