import { useState, useEffect, useCallback } from 'react'
import {
  RefreshCw,
  MoreVertical,
  ChevronLeft,
  ChevronRight,
  Star,
  Archive,
  Trash2,
  Mail,
  Clock,
  ArrowLeft,
  Search,
  Inbox as InboxIcon,
  AlertTriangle,
  Sparkles,
  Activity,
  Type,
  Image,
  Mic,
  FileText,
  Plus as PlusIcon,
  ChevronDown as ChevronDownIcon,
} from 'lucide-react'
import clsx from 'clsx'
import { ChatPanel } from '../../components/containers/ChatPanel'
import { Dashboard } from './Dashboard'
import { getInsights } from '../../lib/services/insights'
import { getSnapshot } from '../../lib/services/snapshot'
import type { BusinessInsight } from '../../lib/workspace/dashboard-types'
import type { SnapshotRecommendation } from '../../lib/services/snapshot'
import { useBusinessStore } from '../../store/business'
import { useWorkspaceStore } from '../../store/workspace'
import * as recordsApi from '../../lib/services/records'

// --- Types ---

type InboxTab = 'primary' | 'insights' | 'attention' | 'recommendations'

type InboxMessage = {
  id: string
  sender: string
  senderEmail: string
  recipient: string
  subject: string
  preview: string
  body: string
  date: string
  fullDate: string
  read: boolean
  starred: boolean
  tab: InboxTab
  avatarColor: string
}

// --- Helpers ---

function areaToSender(area: string): string {
  const map: Record<string, string> = {
    sales: 'Sales Insights',
    finance: 'Finance Alert',
    operations: 'Operations',
    customers: 'Customer Insights',
    inventory: 'Inventory Alert',
    general: 'Tendo AI',
    hr: 'Team Updates',
    marketing: 'Marketing',
  }
  return map[area] || 'Tendo AI'
}

function areaToColor(area: string): string {
  const map: Record<string, string> = {
    sales: 'bg-green-600',
    finance: 'bg-amber-600',
    operations: 'bg-blue-600',
    customers: 'bg-purple-600',
    inventory: 'bg-cyan-600',
    general: 'bg-emerald-600',
    hr: 'bg-pink-600',
    marketing: 'bg-orange-600',
  }
  return map[area] || 'bg-zinc-600'
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  if (diffMins < 60) return `${diffMins}m ago`
  const diffHours = Math.floor(diffMins / 60)
  if (diffHours < 24) return `${diffHours}h ago`
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

// --- Tabs Config ---

const TABS: { id: InboxTab; label: string; badge?: number; badgeColor?: string }[] = [
  { id: 'primary', label: 'Primary' },
  { id: 'insights', label: 'Insights' },
  { id: 'attention', label: 'Needs Attention', badge: 1, badgeColor: 'bg-red-500/20 text-red-400' },
  { id: 'recommendations', label: 'Recommendations', badge: 1, badgeColor: 'bg-amber-500/20 text-amber-400' },
]

// --- Collapsible Section ---

function CollapsibleSection({ title, subtitle, avatarColor, defaultOpen = false, children }: {
  title: string
  subtitle: string
  avatarColor: string
  defaultOpen?: boolean
  children: React.ReactNode
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="mb-4 border-t border-zinc-800/20 bg-zinc-900/20">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-3 px-4 py-3 text-left"
      >
        <div className="min-w-0 flex-1">
          <span className="text-[13px] font-medium text-zinc-200">{title}</span>
          <span className="ml-2 text-[11px] text-zinc-500">{subtitle}</span>
        </div>
        <ChevronDownIcon size={16} className={clsx('text-zinc-500 transition-transform', !open && '-rotate-90')} />
      </button>
      {open && (
        <div className="px-4 pb-4 pt-0">
          {children}
        </div>
      )}
    </div>
  )
}

// --- Message Detail View ---

function MessageDetail({
  message,
  onBack,
}: {
  message: InboxMessage
  onBack: () => void
}) {
  return (
    <div className="flex h-full bg-[#0a0a0a]">
      {/* Left: Record detail */}
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Detail toolbar */}
        <div className="flex items-center gap-1 border-b border-zinc-800/60 px-4 py-2">
          <button type="button" onClick={onBack} className="flex h-8 w-8 items-center justify-center rounded-full text-zinc-400 transition-colors hover:bg-white/5 hover:text-zinc-200" aria-label="Back"><ArrowLeft size={18} /></button>
          <button type="button" className="flex h-8 w-8 items-center justify-center rounded-full text-zinc-400 hover:bg-white/5 hover:text-zinc-200" aria-label="Archive"><Archive size={16} /></button>
          <button type="button" className="flex h-8 w-8 items-center justify-center rounded-full text-zinc-400 hover:bg-white/5 hover:text-zinc-200" aria-label="Delete"><Trash2 size={16} /></button>
          <button type="button" className="flex h-8 w-8 items-center justify-center rounded-full text-zinc-400 hover:bg-white/5 hover:text-zinc-200" aria-label="Mark as unread"><Mail size={16} /></button>
          <button type="button" className="flex h-8 w-8 items-center justify-center rounded-full text-zinc-400 hover:bg-white/5 hover:text-zinc-200" aria-label="More"><MoreVertical size={16} /></button>
          <div className="flex-1" />
          <span className="text-[12px] text-zinc-500">1 of 14</span>
          <button type="button" className="flex h-7 w-7 items-center justify-center rounded-full text-zinc-500 hover:bg-white/5 hover:text-zinc-300" aria-label="Previous"><ChevronLeft size={16} /></button>
          <button type="button" className="flex h-7 w-7 items-center justify-center rounded-full text-zinc-500 hover:bg-white/5 hover:text-zinc-300" aria-label="Next"><ChevronRight size={16} /></button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {/* Subject */}
          <div className="flex items-center gap-2 mb-6">
            <h1 className="text-[18px] font-normal text-zinc-100">{message.subject}</h1>
          </div>

          {/* Source header — collapsible */}
          <CollapsibleSection title={message.sender} subtitle={message.fullDate} avatarColor={message.avatarColor} defaultOpen>
            <div className="text-[14px] leading-relaxed text-zinc-300 whitespace-pre-wrap">{message.body}</div>
          </CollapsibleSection>

          {/* Source input options */}
          <div className="mt-6 flex items-center gap-2 flex-wrap">
            <button type="button" className="flex items-center gap-1.5 rounded-md border border-dashed border-zinc-600 px-3 py-1.5 text-[12px] text-zinc-400 transition-colors hover:border-zinc-500 hover:text-zinc-200">
              <Type size={14} /> Text
            </button>
            <button type="button" className="flex items-center gap-1.5 rounded-md border border-dashed border-zinc-600 px-3 py-1.5 text-[12px] text-zinc-400 transition-colors hover:border-zinc-500 hover:text-zinc-200">
              <Image size={14} /> Image
            </button>
            <button type="button" className="flex items-center gap-1.5 rounded-md border border-dashed border-zinc-600 px-3 py-1.5 text-[12px] text-zinc-400 transition-colors hover:border-zinc-500 hover:text-zinc-200">
              <Mic size={14} /> Audio
            </button>
            <button type="button" className="flex items-center gap-1.5 rounded-md border border-dashed border-zinc-600 px-3 py-1.5 text-[12px] text-zinc-400 transition-colors hover:border-zinc-500 hover:text-zinc-200">
              <FileText size={14} /> PDF
            </button>
            <button type="button" className="flex items-center gap-1.5 rounded-md border border-dashed border-zinc-600 px-3 py-1.5 text-[12px] text-zinc-400 transition-colors hover:border-zinc-500 hover:text-zinc-200">
              <PlusIcon size={14} /> More
            </button>
          </div>
        </div>
      </div>

      {/* Right: Chat session panel */}
      <div className="hidden md:flex w-[340px] shrink-0 flex-col border-l border-zinc-800/60 bg-[#0f0f0f]">
        <ChatPanel recordId={message.id.startsWith('record-') ? message.id.replace('record-', '') : undefined} />
      </div>
    </div>
  )
}

// --- Main Component ---

export function Inbox() {
  const [activeTab, setActiveTab] = useState<InboxTab>('primary')
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [starredIds, setStarredIds] = useState<Set<string>>(new Set())
  const [openMessage, setOpenMessage] = useState<InboxMessage | null>(null)
  const [liveInsights, setLiveInsights] = useState<InboxMessage[]>([])
  const [attentionItems, setAttentionItems] = useState<InboxMessage[]>([])
  const [recommendationItems, setRecommendationItems] = useState<InboxMessage[]>([])
  const [loading, setLoading] = useState(true)
  const { currentProfile } = useBusinessStore()

  // Fetch real insights + snapshot recommendations + records
  useEffect(() => {
    if (!currentProfile?.id) {
      setLoading(false)
      return
    }

    const businessId = currentProfile.id

    Promise.all([
      getInsights(businessId, 20).catch(() => [] as BusinessInsight[]),
      getSnapshot(businessId).catch(() => null),
      recordsApi.getAllRecords().catch(() => []),
    ]).then(async ([insights, snapshot, records]) => {
      // Map records to inbox messages for Primary tab
      const allRecords: InboxMessage[] = records.map((rec) => ({
        id: `record-${rec.id}`,
        sender: 'Record',
        senderEmail: '',
        recipient: '',
        subject: rec.title || 'Untitled',
        preview: `Created ${formatDate(rec.created_at)}`,
        body: rec.title || 'Untitled',
        date: formatDate(rec.updated_at || rec.created_at),
        fullDate: new Date(rec.updated_at || rec.created_at).toLocaleString(),
        read: true,
        starred: false,
        tab: 'primary' as InboxTab,
        avatarColor: 'bg-zinc-600',
      }))

      // Map insights to inbox messages for Primary tab
      const insightMessages: InboxMessage[] = insights.map((ins, i) => ({
        id: `live-${ins.id || i}`,
        sender: areaToSender(ins.area),
        senderEmail: `${ins.area}@tendo.ai`,
        recipient: '',
        subject: ins.insight.slice(0, 80) + (ins.insight.length > 80 ? '...' : ''),
        preview: ins.insight,
        body: ins.insight,
        date: formatDate(ins.created_at),
        fullDate: new Date(ins.created_at).toLocaleString(),
        read: ins.importance < 0.8,
        starred: ins.importance >= 0.9,
        tab: 'primary' as InboxTab,
        avatarColor: areaToColor(ins.area),
      }))

      // Combine records + insights for primary tab
      setLiveInsights([...allRecords, ...insightMessages])

      // Map snapshot recommendations to attention + recommendations tabs
      if (snapshot?.recommendations) {
        const high: InboxMessage[] = []
        const medium: InboxMessage[] = []

        snapshot.recommendations.forEach((rec, i) => {
          const msg: InboxMessage = {
            id: `rec-${i}`,
            sender: 'Tendo AI',
            senderEmail: '',
            recipient: '',
            subject: rec.action,
            preview: rec.reason,
            body: `${rec.action}\n\n${rec.reason}`,
            date: 'Today',
            fullDate: new Date().toLocaleString(),
            read: rec.priority !== 'high',
            starred: rec.priority === 'high',
            tab: rec.priority === 'high' ? 'attention' as InboxTab : 'recommendations' as InboxTab,
            avatarColor: rec.priority === 'high' ? 'bg-red-600' : 'bg-amber-600',
          }

          if (rec.priority === 'high') {
            high.push(msg)
          } else {
            medium.push(msg)
          }
        })

        setAttentionItems(high)
        setRecommendationItems(medium)
      }
    }).finally(() => setLoading(false))
  }, [currentProfile?.id])

  // Listen for new record creation to refresh
  useEffect(() => {
    const handleNewRecord = () => {
      if (currentProfile?.id) {
        recordsApi.getAllRecords().then((records) => {
          const allRecords: InboxMessage[] = records.map((rec) => ({
            id: `record-${rec.id}`,
            sender: 'Record',
            senderEmail: '',
            recipient: '',
            subject: rec.title || 'Untitled',
            preview: `Created ${formatDate(rec.created_at)}`,
            body: rec.title || 'Untitled',
            date: formatDate(rec.updated_at || rec.created_at),
            fullDate: new Date(rec.updated_at || rec.created_at).toLocaleString(),
            read: false,
            starred: false,
            tab: 'primary' as InboxTab,
            avatarColor: 'bg-zinc-600',
          }))
          setLiveInsights((prev) => {
            const nonRecords = prev.filter((m) => !m.id.startsWith('record-'))
            return [...allRecords, ...nonRecords]
          })
        }).catch(() => {})
      }
    }
    window.addEventListener('tendo:open-new-record', handleNewRecord)
    return () => window.removeEventListener('tendo:open-new-record', handleNewRecord)
  }, [currentProfile?.id])

  // Determine which messages to show based on tab
  const getMessages = (): InboxMessage[] => {
    switch (activeTab) {
      case 'primary':
        return liveInsights
      case 'attention':
        return attentionItems
      case 'recommendations':
        return recommendationItems
      default:
        return []
    }
  }

  const filteredMessages = getMessages()

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const toggleSelectAll = () => {
    if (selectedIds.size === filteredMessages.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(filteredMessages.map((m) => m.id)))
    }
  }

  const toggleStar = (id: string) => {
    setStarredIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  // If a message is open, show detail view
  if (openMessage) {
    return <MessageDetail message={openMessage} onBack={() => setOpenMessage(null)} />
  }

  return (
    <div className="flex h-full flex-col bg-[#0a0a0a]">
      {/* Toolbar */}
      <div className="flex items-center gap-2 border-b border-zinc-800/60 px-4 py-2">
        <button
          type="button"
          onClick={toggleSelectAll}
          className="flex h-5 w-5 items-center justify-center rounded border border-zinc-600 text-zinc-400 transition-colors hover:border-zinc-500 hover:bg-zinc-800"
          aria-label="Select all"
        >
          {selectedIds.size > 0 && selectedIds.size === filteredMessages.length && (
            <span className="h-2.5 w-2.5 rounded-sm bg-emerald-500" />
          )}
          {selectedIds.size > 0 && selectedIds.size < filteredMessages.length && (
            <span className="h-0.5 w-2.5 bg-emerald-500" />
          )}
        </button>
        <button type="button" className="flex h-8 w-8 items-center justify-center rounded-full text-zinc-400 transition-colors hover:bg-white/5 hover:text-zinc-200" aria-label="Refresh">
          <RefreshCw size={16} />
        </button>

        {/* Search bar */}
        <div className="flex-1">
          <div className="relative w-full max-w-[440px]">
            <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-zinc-500" />
            <input
              type="text"
              placeholder="Search..."
              className="w-full rounded-md border border-zinc-800 bg-zinc-900/50 py-1 pl-8 pr-8 text-[12px] text-zinc-300 placeholder-zinc-500 transition-colors focus:border-zinc-700 focus:outline-none"
            />
            <kbd className="absolute right-2.5 top-1/2 -translate-y-1/2 hidden rounded border border-zinc-700/60 bg-zinc-800/50 px-1 py-0.5 text-[9px] font-medium text-zinc-500 sm:inline">⌘K</kbd>
          </div>
        </div>

        <button type="button" className="flex h-8 w-8 items-center justify-center rounded-full text-zinc-400 transition-colors hover:bg-white/5 hover:text-zinc-200" aria-label="More actions">
          <MoreVertical size={16} />
        </button>
        <span className="text-[12px] text-zinc-500">1–{filteredMessages.length} of {filteredMessages.length}</span>
        <button type="button" className="flex h-7 w-7 items-center justify-center rounded-full text-zinc-500 hover:bg-white/5 hover:text-zinc-300" aria-label="Previous page">
          <ChevronLeft size={16} />
        </button>
        <button type="button" className="flex h-7 w-7 items-center justify-center rounded-full text-zinc-500 hover:bg-white/5 hover:text-zinc-300" aria-label="Next page">
          <ChevronRight size={16} />
        </button>
      </div>

      {/* Category tabs */}
      <div className="flex items-center border-b border-zinc-800/60">
        {TABS.map((tab) => {
          return (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            className={clsx(
              'relative flex flex-1 items-center justify-center gap-1.5 px-4 py-3 text-[13px] font-medium transition-colors',
              activeTab === tab.id
                ? 'text-zinc-100'
                : 'text-zinc-500 hover:text-zinc-300 hover:bg-white/[0.02]'
            )}
          >
            {tab.label}
            {tab.badge && (
              <span className={clsx('rounded-full px-1.5 py-0.5 text-[10px] font-semibold', tab.badgeColor || 'bg-emerald-500/20 text-emerald-400')}>
                {tab.badge} new
              </span>
            )}
            {activeTab === tab.id && (
              <span className="absolute inset-x-0 bottom-0 h-[2px] rounded-full bg-zinc-400" />
            )}
          </button>
          )
        })}
      </div>

      {/* Content area — show Dashboard for insights tab, message list for others */}
      {activeTab === 'insights' ? (
        <div className="flex-1 overflow-y-auto">
          <Dashboard />
        </div>
      ) : filteredMessages.length === 0 ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center px-6">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-zinc-800/60">
              {activeTab === 'primary' && <Activity size={22} className="text-zinc-500" />}
              {activeTab === 'attention' && <AlertTriangle size={22} className="text-red-400" />}
              {activeTab === 'recommendations' && <Sparkles size={22} className="text-amber-400" />}
            </div>
            <p className="text-[14px] font-medium text-zinc-300">
              {activeTab === 'primary' && 'No activities yet'}
              {activeTab === 'attention' && 'Nothing needs attention'}
              {activeTab === 'recommendations' && 'No recommendations yet'}
            </p>
            <p className="mt-1 text-[12px] text-zinc-500">
              {activeTab === 'primary' && 'Business activities and records will appear here as you interact with Tendo.'}
              {activeTab === 'attention' && 'High priority items that require your action will show up here.'}
              {activeTab === 'recommendations' && 'Suggestions to improve your business will appear here.'}
            </p>
          </div>
        </div>
      ) : (
      <div className="flex-1 overflow-y-auto">
        {filteredMessages.map((msg) => (
          <div
            key={msg.id}
            onClick={() => setOpenMessage(msg)}
            className={clsx(
              'group flex items-center gap-0 border-b border-zinc-800/40 px-4 py-1.5 transition-colors cursor-pointer',
              !msg.read ? 'bg-zinc-900/50' : 'bg-transparent',
              selectedIds.has(msg.id) && 'bg-emerald-500/5',
              'hover:bg-white/[0.03] hover:shadow-[inset_2px_0_0_0_#3ecf8e]'
            )}
          >
            {/* Checkbox */}
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); toggleSelect(msg.id) }}
              className="flex h-5 w-5 shrink-0 items-center justify-center rounded border border-zinc-700 text-zinc-400 transition-colors hover:border-zinc-500 mr-2"
              aria-label={`Select message from ${msg.sender}`}
            >
              {selectedIds.has(msg.id) && (
                <span className="h-2.5 w-2.5 rounded-sm bg-emerald-500" />
              )}
            </button>

            {/* Star */}
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); toggleStar(msg.id) }}
              className={clsx(
                'flex h-7 w-7 shrink-0 items-center justify-center rounded-full transition-colors mr-2',
                starredIds.has(msg.id) ? 'text-yellow-400' : 'text-zinc-600 hover:text-zinc-400'
              )}
              aria-label={starredIds.has(msg.id) ? 'Unstar' : 'Star'}
            >
              <Star size={16} fill={starredIds.has(msg.id) ? 'currentColor' : 'none'} />
            </button>

            {/* Sender */}
            <span className={clsx('w-[160px] shrink-0 truncate text-[13px]', !msg.read ? 'font-semibold text-zinc-100' : 'text-zinc-400')}>
              {msg.sender}
            </span>

            {/* Subject + preview */}
            <div className="min-w-0 flex-1 flex items-baseline gap-1 mr-3">
              <span className={clsx('shrink-0 truncate text-[13px]', !msg.read ? 'font-semibold text-zinc-100' : 'text-zinc-300')}>
                {msg.subject}
              </span>
              <span className="text-zinc-600 text-[13px] shrink-0">-</span>
              <span className="min-w-0 truncate text-[13px] text-zinc-500">{msg.preview}</span>
            </div>

            {/* Hover actions */}
            <div className="hidden shrink-0 items-center gap-0.5 group-hover:flex mr-2">
              <button type="button" className="flex h-7 w-7 items-center justify-center rounded-full text-zinc-500 hover:bg-white/5 hover:text-zinc-300" aria-label="Archive" onClick={(e) => e.stopPropagation()}>
                <Archive size={15} />
              </button>
              <button type="button" className="flex h-7 w-7 items-center justify-center rounded-full text-zinc-500 hover:bg-white/5 hover:text-zinc-300" aria-label="Delete" onClick={(e) => e.stopPropagation()}>
                <Trash2 size={15} />
              </button>
              <button type="button" className="flex h-7 w-7 items-center justify-center rounded-full text-zinc-500 hover:bg-white/5 hover:text-zinc-300" aria-label="Mark as read" onClick={(e) => e.stopPropagation()}>
                <Mail size={15} />
              </button>
              <button type="button" className="flex h-7 w-7 items-center justify-center rounded-full text-zinc-500 hover:bg-white/5 hover:text-zinc-300" aria-label="Snooze" onClick={(e) => e.stopPropagation()}>
                <Clock size={15} />
              </button>
            </div>

            {/* Date */}
            <span className={clsx('shrink-0 text-[12px] tabular-nums', !msg.read ? 'font-semibold text-zinc-200' : 'text-zinc-500')}>
              {msg.date}
            </span>
          </div>
        ))}
      </div>
      )}
    </div>
  )
}
