import { useState, useEffect } from 'react'
import { Plus, History, X } from 'lucide-react'
import { Conversation } from '../../pages/Conversation'
import { useBusinessStore } from '../../store/business'
import { listSessions, createSession, getSessionMessages, type ChatSession, type ChatMessage } from '../../lib/services/conversations'
import type { MessageItem } from './ConversationPage'

export function ChatPanel({ recordId }: { recordId?: string }) {
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [activeSessionId, setActiveSessionId] = useState<string>('')
  const [initialMessages, setInitialMessages] = useState<MessageItem[]>([])
  const [showHistory, setShowHistory] = useState(false)
  const [collapsed, setCollapsed] = useState(false)
  const [loading, setLoading] = useState(true)
  const [loadingMessages, setLoadingMessages] = useState(false)
  const { currentProfile } = useBusinessStore()
  const businessId = currentProfile?.id || ''

  // Load sessions on mount or business change
  useEffect(() => {
    if (!businessId) return

    setLoading(true)
    listSessions(businessId, recordId)
      .then((data) => {
        setSessions(data)
        if (data.length > 0) {
          setActiveSessionId(data[0].id)
        }
      })
      .catch(() => {
        setSessions([])
      })
      .finally(() => setLoading(false))
  }, [businessId, recordId])

  // Load messages when active session changes — fetch in batches of 20
  useEffect(() => {
    if (!activeSessionId || !businessId) {
      setInitialMessages([])
      return
    }

    let cancelled = false
    setLoadingMessages(true)

    async function loadAllMessages() {
      const PAGE_SIZE = 20
      let offset = 0
      let allMessages: MessageItem[] = []

      while (true) {
        const batch = await getSessionMessages(activeSessionId, businessId, PAGE_SIZE, offset)
        if (cancelled) return

        if (batch.length === 0) break

        const mapped = batch.map((m, i) => ({
          id: `msg-${offset + i}`,
          role: m.role as 'user' | 'assistant',
          content: m.content,
          type: 'text' as const,
        }))

        allMessages = [...allMessages, ...mapped]
        setInitialMessages([...allMessages])

        if (batch.length < PAGE_SIZE) break
        offset += PAGE_SIZE
      }
    }

    loadAllMessages().finally(() => {
      if (!cancelled) setLoadingMessages(false)
    })

    return () => { cancelled = true }
  }, [activeSessionId, businessId])

  const handleNewSession = async () => {
    if (!businessId) return
    try {
      const session = await createSession(businessId, 'New Session', recordId)
      setSessions((prev) => [session, ...prev])
      setActiveSessionId(session.id)
      setInitialMessages([])
    } catch {
      // Error handled by http service
    }
  }

  const handleCloseSession = (id: string) => {
    setSessions((prev) => prev.filter((s) => s.id !== id))
    if (activeSessionId === id) {
      const remaining = sessions.filter((s) => s.id !== id)
      setActiveSessionId(remaining.length > 0 ? remaining[0].id : '')
    }
  }

  if (collapsed) {
    return (
      <button
        onClick={() => setCollapsed(false)}
        className="flex h-full w-10 items-center justify-center border-l border-zinc-800/60 bg-[#0f0f0f] text-zinc-400 hover:text-zinc-300"
        title="Open chat"
      >
        <span className="rotate-90 whitespace-nowrap text-[10px] font-medium tracking-wide">Chat</span>
      </button>
    )
  }

  return (
    <div className="flex h-full flex-col bg-[#0f0f0f]">
      {/* Tab bar */}
      <div className="flex min-h-[36px] items-center gap-0.5 overflow-x-auto border-b border-zinc-800/60 bg-[#0a0a0a] px-1">
        {sessions.slice(0, 5).map((session) => (
          <div
            key={session.id}
            onClick={() => setActiveSessionId(session.id)}
            className={`flex cursor-pointer items-center gap-1 rounded-t-md px-2.5 py-1.5 text-[11px] transition-colors ${
              activeSessionId === session.id
                ? 'bg-[#0f0f0f] text-zinc-200 border border-zinc-800/60 border-b-transparent'
                : 'text-zinc-400 hover:text-zinc-300'
            }`}
          >
            <span className="max-w-[100px] truncate">{session.title}</span>
            <button
              onClick={(e) => {
                e.stopPropagation()
                handleCloseSession(session.id)
              }}
              className="ml-0.5 rounded p-0.5 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-300"
            >
              <X size={10} />
            </button>
          </div>
        ))}

        <button
          onClick={handleNewSession}
          className="flex items-center gap-1 px-2 py-1.5 text-[11px] text-zinc-400 hover:text-zinc-300"
          title="New session"
        >
          New <Plus size={12} />
        </button>

        <div className="flex-1" />

        <button
          onClick={() => setShowHistory(!showHistory)}
          className={`rounded p-1 transition-colors ${showHistory ? 'bg-zinc-800 text-zinc-200' : 'text-zinc-400 hover:text-zinc-300'}`}
          title="Session history"
        >
          <History size={14} />
        </button>
      </div>

      {/* History dropdown */}
      {showHistory && (
        <div className="border-b border-zinc-800/60 bg-[#141414] px-3 py-2 max-h-[200px] overflow-y-auto">
          <p className="text-[10px] font-medium uppercase tracking-wide text-zinc-400 mb-1.5">All sessions</p>
          {sessions.length > 0 ? (
            sessions.map((s) => (
              <button
                key={s.id}
                onClick={() => { setActiveSessionId(s.id); setShowHistory(false) }}
                className={`flex w-full cursor-pointer items-center rounded px-2 py-1 text-[11px] transition-colors hover:bg-zinc-800 ${
                  s.id === activeSessionId ? 'text-emerald-400' : 'text-zinc-400'
                }`}
              >
                <span className="truncate">{s.title}</span>
                <span className="ml-auto text-[9px] text-zinc-600">{new Date(s.created_at).toLocaleDateString()}</span>
              </button>
            ))
          ) : (
            <p className="text-[11px] text-zinc-400">No sessions yet</p>
          )}
        </div>
      )}

      {/* Chat area */}
      <div className="min-h-0 flex-1">
        {loading ? (
          <div className="flex h-full items-center justify-center">
            <span className="text-xs text-zinc-500">Loading...</span>
          </div>
        ) : loadingMessages ? (
          <div className="flex h-full items-center justify-center">
            <div className="flex flex-col items-center gap-2">
              <span className="flex items-center gap-1">
                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-zinc-500 [animation-delay:0ms]" />
                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-zinc-500 [animation-delay:150ms]" />
                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-zinc-500 [animation-delay:300ms]" />
              </span>
              <span className="text-[11px] text-zinc-500">Loading messages...</span>
            </div>
          </div>
        ) : activeSessionId ? (
          <Conversation
            key={activeSessionId}
            initialMessages={initialMessages}
            sessionId={activeSessionId}
            sessionTitle={sessions.find(s => s.id === activeSessionId)?.title}
            fullScreen={false}
            showHeader={false}
            characterRightOffset={290}
          />
        ) : (
          <div className="flex h-full items-center justify-center">
            <button onClick={handleNewSession} className="text-xs text-zinc-400 hover:text-zinc-300">
              Start a new conversation
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
