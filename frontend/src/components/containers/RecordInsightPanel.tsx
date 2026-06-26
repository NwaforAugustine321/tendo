import { useEffect, useState } from 'react'
import { Sparkles, Lightbulb, Loader2 } from 'lucide-react'
import clsx from 'clsx'
import { useWorkspaceStore } from '../../store/workspace'
import * as recordsApi from '../../lib/services/records'

type InsightEntry = {
  version: number
  timestamp: string
  insight: string
  suggested_questions: string[]
}

export function RecordInsightPanel() {
  const activeRecordId = useWorkspaceStore((s) => s.activeRecordId)
  const [insights, setInsights] = useState<InsightEntry[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!activeRecordId) {
      setInsights([])
      return
    }

    setLoading(true)
    setInsights([])

    recordsApi.getRecord(activeRecordId).then((record) => {
      const aiInsight = record?.ai_insight || []
      setInsights(aiInsight)
      setLoading(false)
    }).catch(() => {
      setLoading(false)
    })
  }, [activeRecordId])

  useEffect(() => {
    if (!activeRecordId) return

    const handleStatus = (e: Event) => {
      const detail = (e as CustomEvent).detail
      if (detail?.record_id === activeRecordId && detail?.status === 'completed') {
        recordsApi.getRecord(activeRecordId).then((record) => {
          const aiInsight = record?.ai_insight || []
          setInsights(aiInsight)
        }).catch(() => {})
      }
    }

    window.addEventListener('tendo:record-processing', handleStatus)
    return () => window.removeEventListener('tendo:record-processing', handleStatus)
  }, [activeRecordId])

  if (!activeRecordId) return null

  return (
    <div className="w-[400px] shrink-0 border-r border-zinc-800/60 bg-[#0f0f0f] flex flex-col min-h-0 overflow-hidden">
      <div className="flex items-center gap-2 border-b border-zinc-800/60 px-4 py-3">
        <Sparkles size={14} className="text-[#3ecf8e]" />
        <span className="text-xs font-medium text-zinc-300">{import.meta.env.VITE_AGENT_NAME || 'Jay'} Insights</span>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {loading && (
          <div className="flex items-center gap-2 py-4 justify-center">
            <Loader2 size={14} className="animate-spin text-[#3ecf8e]" />
            <span className="text-xs text-zinc-500">Loading insights...</span>
          </div>
        )}

        {!loading && insights.length === 0 && (
          <div className="py-6 text-center">
            <Lightbulb size={20} className="mx-auto mb-2 text-zinc-600" />
            <p className="text-xs text-zinc-500">No insights yet</p>
            <p className="text-[10px] text-zinc-600 mt-1">Capture content to generate insights</p>
          </div>
        )}

        {insights.map((entry) => (
          <div
            key={entry.version}
            className="rounded-lg border border-white/5 bg-[#141414] p-3 cursor-pointer"
          >
            <p className="text-xs leading-relaxed text-zinc-300 mb-2">
              {entry.insight}
            </p>

            {entry.suggested_questions.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-1">
                {entry.suggested_questions.map((q, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => {
                      window.dispatchEvent(new CustomEvent('tendo:send-chat-message', { detail: { text: q } }))
                    }}
                    className={clsx(
                      'flex items-center gap-1 rounded-full px-2.5 py-1',
                      'border border-zinc-700/50 bg-[#1a1a1a]',
                      'text-[10px] text-zinc-400 hover:text-zinc-200 hover:border-zinc-600',
                      'transition-colors text-left'
                    )}
                  >
                    <Lightbulb size={10} className="text-[#3ecf8e] shrink-0" />
                    <span>{q}</span>
                  </button>
                ))}
              </div>
            )}

            <div className="mt-2 flex items-center gap-2 text-[9px] text-zinc-600">
             
             
              <span>{new Date(entry.timestamp).toLocaleString()}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
