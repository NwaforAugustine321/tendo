import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Type, Image, Mic, FileText, X, Plus, Camera, AudioLines, Sparkles, Lightbulb, Loader2 } from 'lucide-react'
import clsx from 'clsx'
import { toast } from 'sonner'
import { FloatingPanel } from './FloatingPanel'
import { useWorkspaceStore } from '../../store/workspace'
import type { Record, RecordEntry, EntryType } from '../../lib/workspace/types'
import * as recordsApi from '../../lib/services/records'

const ENTRY_TYPE_ICONS: { type: EntryType; label: string; icon: typeof Type }[] = [
  { type: 'text', label: 'Text', icon: Type },
  { type: 'image', label: 'Image', icon: Image },
  { type: 'audio', label: 'Audio', icon: Mic },
  { type: 'pdf', label: 'PDF', icon: FileText },
]

const MORE_ENTRY_TYPES: { type: EntryType; label: string; icon: typeof Type }[] = [
  { type: 'camera', label: 'Camera', icon: Camera },
  { type: 'voice', label: 'Voice', icon: AudioLines },
]

const WORD_LIMIT = 25

function truncateWords(text: string, limit: number): string {
  const words = text.split(/\s+/)
  if (words.length <= limit) return text
  return words.slice(0, limit).join(' ') + '...'
}

function isLongText(text: string): boolean {
  return text.split(/\s+/).length > WORD_LIMIT || text.length > 400
}

type InsightEntry = {
  id: string
  insight: string
  suggested_questions: string[]
  timestamp: string
}

function RecordContentTab({ recordId }: { recordId: string }) {
  const [localEntries, setLocalEntries] = useState<RecordEntry[]>([])
  const [capturedIds, setCapturedIds] = useState<Set<string>>(new Set())
  const [, setCapturingIds] = useState<Set<string>>(new Set())
  const [showMoreTypes, setShowMoreTypes] = useState(false)
  const textareaRefs = useRef<Map<string, HTMLTextAreaElement>>(new Map())
  const prevRecordIdRef = useRef<string | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (recordId !== prevRecordIdRef.current) {
      prevRecordIdRef.current = recordId
      if (!recordId) {
        setLocalEntries([])
        return
      }
      setLocalEntries([])
      recordsApi.getRecordContents(recordId).then((contents) => {
        const entries: RecordEntry[] = contents.map((c) => ({
          id: c.id,
          type: (c.content_type || 'text') as EntryType,
          content: c.content,
          createdAt: c.created_at,
        }))
        setLocalEntries(entries)
        setCapturedIds(new Set(entries.map((e) => e.id)))
      }).catch(() => {})
    }
  }, [recordId])

  const handleEntryChange = useCallback((entryId: string, newContent: string) => {
    setLocalEntries((prev) =>
      prev.map((e) => (e.id === entryId ? { ...e, content: newContent } : e))
    )
  }, [])

  const handleAddEntry = useCallback((type: EntryType) => {
    const newEntry: RecordEntry = {
      id: crypto.randomUUID(),
      type,
      content: '',
      createdAt: new Date().toISOString(),
    }
    setLocalEntries((prev) => [...prev, newEntry])
    setTimeout(() => {
      scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
      if (type === 'text') {
        textareaRefs.current.get(newEntry.id)?.focus()
      }
    }, 50)
  }, [])

  const handleCapture = useCallback(async (entryId: string) => {
    if (!recordId) return
    const entry = localEntries.find((e) => e.id === entryId)
    if (!entry || !entry.content.trim()) return
    setCapturingIds((prev) => new Set(prev).add(entryId))
    try {
      await recordsApi.addRecordContent(recordId, entry.type, entry.content)
      setCapturedIds((prev) => new Set(prev).add(entryId))
      toast.success('Content captured')
    } catch {
      toast.error('Failed to capture content')
    } finally {
      setCapturingIds((prev) => { const n = new Set(prev); n.delete(entryId); return n })
    }
  }, [recordId, localEntries])

  const handleRemoveEntry = useCallback((entryId: string) => {
    setLocalEntries((prev) => prev.filter((e) => e.id !== entryId))
  }, [])

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Entries — scrollable area */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-3 space-y-3">
        {localEntries.length === 0 && (
          <div className="flex flex-col items-center justify-center py-10 text-center">
            <p className="text-xs text-zinc-500 mb-1">Add content to this record</p>
            <p className="text-[10px] text-zinc-600">Choose an input type below</p>
          </div>
        )}

        {localEntries.map((entry) => (
          <div key={entry.id} className="group relative rounded-lg border border-white/5 bg-[#141414] p-3">
            {!capturedIds.has(entry.id) && (
              <button
                type="button"
                onClick={() => handleRemoveEntry(entry.id)}
                className="absolute right-2 top-2 rounded p-1 text-zinc-600 opacity-0 transition-opacity group-hover:opacity-100 hover:bg-white/10 hover:text-zinc-300"
              >
                <X size={11} />
              </button>
            )}

            <div className="mb-2 flex items-center gap-1.5">
              {entry.type === 'text' && <Type size={11} className="text-zinc-500" />}
              {entry.type === 'image' && <Image size={11} className="text-zinc-500" />}
              {entry.type === 'audio' && <Mic size={11} className="text-zinc-500" />}
              {entry.type === 'pdf' && <FileText size={11} className="text-zinc-500" />}
              <span className="text-[9px] uppercase tracking-wide text-zinc-600">{entry.type}</span>
            </div>

            {entry.type === 'text' && (
              capturedIds.has(entry.id) ? (
                <p className="text-xs text-zinc-300 leading-relaxed">{entry.content.length > 200 ? entry.content.slice(0, 200) + '...' : entry.content}</p>
              ) : (
                <textarea
                  ref={(el) => { if (el) { textareaRefs.current.set(entry.id, el); el.style.height = 'auto'; el.style.height = el.scrollHeight + 'px' } else textareaRefs.current.delete(entry.id) }}
                  value={entry.content}
                  onChange={(e) => { handleEntryChange(entry.id, e.target.value); e.target.style.height = 'auto'; e.target.style.height = e.target.scrollHeight + 'px' }}
                  placeholder="Type something..."
                  className="w-full min-h-[50px] resize-none overflow-hidden bg-transparent text-xs leading-relaxed text-zinc-200 placeholder-zinc-600 focus:outline-none"
                />
              )
            )}

            {entry.type === 'image' && (
              <div className="flex items-center justify-center rounded-md border border-dashed border-zinc-700 py-4">
                {entry.content ? <img src={entry.content} alt="" className="max-h-32 rounded" /> : (
                  <label className="cursor-pointer text-[10px] text-zinc-500 hover:text-zinc-300">
                    Click to upload image
                    <input type="file" accept="image/*" className="hidden" onChange={(e) => { const file = e.target.files?.[0]; if (file) { const reader = new FileReader(); reader.onload = () => handleEntryChange(entry.id, reader.result as string); reader.readAsDataURL(file) } }} />
                  </label>
                )}
              </div>
            )}

            {entry.type === 'audio' && (
              <div className="flex items-center justify-center rounded-md border border-dashed border-zinc-700 py-4">
                {entry.content ? <audio controls src={entry.content} className="w-full max-w-xs" /> : (
                  <label className="cursor-pointer text-[10px] text-zinc-500 hover:text-zinc-300">
                    Click to upload audio
                    <input type="file" accept="audio/*" className="hidden" onChange={(e) => { const file = e.target.files?.[0]; if (file) { const reader = new FileReader(); reader.onload = () => handleEntryChange(entry.id, reader.result as string); reader.readAsDataURL(file) } }} />
                  </label>
                )}
              </div>
            )}

            {entry.type === 'pdf' && (
              <div className="flex items-center justify-center rounded-md border border-dashed border-zinc-700 py-4">
                {entry.content ? <a href={entry.content} target="_blank" rel="noopener noreferrer" className="text-[10px] text-[#3ecf8e] hover:underline">View PDF</a> : (
                  <label className="cursor-pointer text-[10px] text-zinc-500 hover:text-zinc-300">
                    Click to upload PDF
                    <input type="file" accept=".pdf" className="hidden" onChange={(e) => { const file = e.target.files?.[0]; if (file) { const reader = new FileReader(); reader.onload = () => handleEntryChange(entry.id, reader.result as string); reader.readAsDataURL(file) } }} />
                  </label>
                )}
              </div>
            )}

            {!capturedIds.has(entry.id) && (
              <button
                type="button"
                onClick={() => handleCapture(entry.id)}
                disabled={!entry.content.trim()}
                className={clsx(
                  'mt-2 flex items-center gap-1.5 rounded-md px-2.5 py-1 text-[10px] font-medium border transition-colors',
                  entry.content.trim()
                    ? 'border-[#3ecf8e]/40 text-[#3ecf8e] hover:border-[#3ecf8e] hover:bg-[#3ecf8e]/10 cursor-pointer'
                    : 'border-zinc-700 text-zinc-600 cursor-not-allowed opacity-50'
                )}
              >
                Capture
              </button>
            )}
          </div>
        ))}
      </div>

      {/* Fixed bottom — input source buttons */}
      <div className="shrink-0 flex items-center gap-1.5 px-3 py-2.5 border-t border-zinc-800/40 flex-wrap">
        <button
          type="button"
          onClick={() => handleAddEntry('text')}
          className="flex items-center gap-1 rounded-md px-2 py-1 border border-dashed border-zinc-700 text-zinc-500 hover:border-zinc-500 hover:text-zinc-200 hover:bg-white/5 text-[10px] font-medium transition-colors"
        >
          <Type size={11} /> Text
        </button>
        <label className="flex items-center gap-1 rounded-md px-2 py-1 border border-dashed border-zinc-700 text-zinc-500 hover:border-zinc-500 hover:text-zinc-200 hover:bg-white/5 text-[10px] font-medium transition-colors cursor-pointer">
          <Image size={11} /> Image
          <input type="file" accept="image/*" className="hidden" onChange={(e) => { const f = e.target.files?.[0]; if (f) { const reader = new FileReader(); reader.onload = () => { handleAddEntry('image'); setTimeout(() => { const entries = document.querySelectorAll('[data-entry-type]'); }, 0) }; reader.readAsDataURL(f) } }} />
        </label>
        <label className="flex items-center gap-1 rounded-md px-2 py-1 border border-dashed border-zinc-700 text-zinc-500 hover:border-zinc-500 hover:text-zinc-200 hover:bg-white/5 text-[10px] font-medium transition-colors cursor-pointer">
          <Mic size={11} /> Audio
          <input type="file" accept="audio/*" className="hidden" onChange={(e) => { const f = e.target.files?.[0]; if (f) { const reader = new FileReader(); reader.onload = () => handleEntryChange(crypto.randomUUID(), reader.result as string); reader.readAsDataURL(f) } }} />
        </label>
        <label className="flex items-center gap-1 rounded-md px-2 py-1 border border-dashed border-zinc-700 text-zinc-500 hover:border-zinc-500 hover:text-zinc-200 hover:bg-white/5 text-[10px] font-medium transition-colors cursor-pointer">
          <FileText size={11} /> PDF
          <input type="file" accept=".pdf" className="hidden" onChange={(e) => { const f = e.target.files?.[0]; if (f) { const reader = new FileReader(); reader.onload = () => handleEntryChange(crypto.randomUUID(), reader.result as string); reader.readAsDataURL(f) } }} />
        </label>
      </div>
    </div>
  )
}

export function RecordFloatingPanel() {
  const { openRecordIds } = useWorkspaceStore()

  if (openRecordIds.length === 0) return null

  return (
    <>
      {openRecordIds.map((recordId, index) => (
        <SingleRecordPanel key={recordId} recordId={recordId} index={index} />
      ))}
    </>
  )
}

function SingleRecordPanel({ recordId, index }: { recordId: string; index: number }) {
  const { records } = useWorkspaceStore()

  const activeRecord: Record | null = useMemo(() => {
    for (const [, folderRecords] of records) {
      const found = folderRecords.find((r) => r.id === recordId)
      if (found) return found
    }
    return null
  }, [recordId, records])

  const title = activeRecord?.title || 'Record'

  return (
    <FloatingPanel
      visible={true}
      title={title}
      onClose={() => useWorkspaceStore.getState().closeRecord(recordId)}
      defaultWidth={600}
      defaultHeight={420}
      offsetIndex={index}
    >
      {/* Content — no tabs, just record content */}
      <div className="min-h-0 flex-1 flex flex-col overflow-hidden">
        <RecordContentTab recordId={recordId} />
      </div>
    </FloatingPanel>
  )
}
