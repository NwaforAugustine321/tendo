import { useState } from 'react'
import { Plus, History, X } from 'lucide-react'
import { Conversation } from '../../pages/Conversation'
import { useBusinessStore } from '../../store/business'

type ChatSession = {
  id: string
  title: string
}

export function ChatPanel() {
  const [sessions, setSessions] = useState<ChatSession[]>([
    { id: 'default', title: 'New Session' },
  ])
  const [activeSession, setActiveSession] = useState('default')
  const [showHistory, setShowHistory] = useState(false)
  const [collapsed, setCollapsed] = useState(false)
  const { currentProfile } = useBusinessStore()

  const handleNewSession = () => {
    const id = `session-${Date.now()}`
    setSessions((prev) => [...prev, { id, title: `New S` }])
    setActiveSession(id)
  }

  const handleCloseSession = (id: string) => {
    setSessions((prev) => prev.filter((s) => s.id !== id))
    if (activeSession === id) {
      const remaining = sessions.filter((s) => s.id !== id)
      setActiveSession(remaining.length > 0 ? remaining[0].id : '')
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
    <div className="flex h-full w-[380px] flex-shrink-0 flex-col border-l border-zinc-800/60 bg-[#0f0f0f]">
      {/* Tab bar */}
      <div className="flex min-h-[36px] items-center gap-0.5 overflow-x-auto border-b border-zinc-800/60 bg-[#0a0a0a] px-1">
        {sessions.map((session) => (
          <div
            key={session.id}
            onClick={() => setActiveSession(session.id)}
            className={`flex cursor-pointer items-center gap-1 rounded-t-md px-2.5 py-1.5 text-[11px] transition-colors ${
              activeSession === session.id
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
          New S <Plus size={12} />
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
        <div className="border-b border-zinc-800/60 bg-[#141414] px-3 py-2">
          <p className="text-[10px] font-medium uppercase tracking-wide text-zinc-400 mb-1.5">Recent sessions</p>
          {sessions.length > 0 ? (
            sessions.map((s) => (
              <button
                key={s.id}
                onClick={() => { setActiveSession(s.id); setShowHistory(false) }}
                className={`flex w-full cursor-pointer items-center rounded px-2 py-1 text-[11px] transition-colors hover:bg-zinc-800 ${
                  s.id === activeSession ? 'text-emerald-400' : 'text-zinc-400'
                }`}
              >
                {s.title}
              </button>
            ))
          ) : (
            <p className="text-[11px] text-zinc-400">No sessions yet</p>
          )}
        </div>
      )}

      {/* Chat area */}
      <div className="min-h-0 flex-1">
        {activeSession && (
          <Conversation
            key={activeSession}
            fullScreen={false}
            showHeader={false}
            flipCharacter
            characterRightOffset={290}
          />
        )}
      </div>
    </div>
  )
}
