import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { ChevronRight, Type, Image, Mic, FileText, X } from 'lucide-react'
import clsx from 'clsx'
import { useWorkspaceStore } from '../../store/workspace'
import { InsightsFeed } from './InsightsFeed'
import { BREADCRUMB_MAX_TITLE_LENGTH } from '../../lib/workspace/constants'
import type { Record, RecordEntry, EntryType } from '../../lib/workspace/types'

const AUTOSAVE_DEBOUNCE_MS = 1000

const ENTRY_TYPE_ICONS: { type: EntryType; label: string; icon: typeof Type }[] = [
  { type: 'text', label: 'Text', icon: Type },
  { type: 'image', label: 'Image', icon: Image },
  { type: 'audio', label: 'Audio', icon: Mic },
  { type: 'pdf', label: 'PDF', icon: FileText },
]

export function WorkspaceContent() {
  const {
    folders,
    records,
    activeRecordId,
    toggleFolderExpanded,
    saveRecord,
  } = useWorkspaceStore()

  const [transitioning, setTransitioning] = useState(false)
  const [error, setError] = useState(false)
  const [localEntries, setLocalEntries] = useState<RecordEntry[]>([])

  const textareaRefs = useRef<Map<string, HTMLTextAreaElement>>(new Map())
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const prevRecordIdRef = useRef<string | null>(null)
  const prefersReducedMotion = useRef(false)

  useEffect(() => {
    prefersReducedMotion.current = window.matchMedia(
      '(prefers-reduced-motion: reduce)'
    ).matches
  }, [])

  // Find the active record
  const activeRecord: Record | null = useMemo(() => {
    if (!activeRecordId) return null
    for (const [, folderRecords] of records) {
      const found = folderRecords.find((r) => r.id === activeRecordId)
      if (found) return found
    }
    return null
  }, [activeRecordId, records])

  // Find the folder for the active record
  const activeFolder = useMemo(() => {
    if (!activeRecord) return null
    return folders.find((f) => f.id === activeRecord.folderId) || null
  }, [activeRecord, folders])

  // Load entries when record changes
  useEffect(() => {
    if (activeRecordId !== prevRecordIdRef.current) {
      if (prevRecordIdRef.current !== null && !prefersReducedMotion.current) {
        setTransitioning(true)
        const timer = setTimeout(() => setTransitioning(false), 300)
        prevRecordIdRef.current = activeRecordId
        if (activeRecord) {
          setLocalEntries(activeRecord.entries || [])
          setError(false)
        } else if (activeRecordId) {
          setError(true)
        }
        return () => clearTimeout(timer)
      } else {
        prevRecordIdRef.current = activeRecordId
        if (activeRecord) {
          setLocalEntries(activeRecord.entries || [])
          setError(false)
        } else if (activeRecordId) {
          setError(true)
        }
      }
    }
  }, [activeRecordId, activeRecord])

  // Auto-save with debounce
  const triggerSave = useCallback(() => {
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current)
    if (!activeRecordId) return
    saveTimerRef.current = setTimeout(() => {
      // Serialize entries to content for now
      const content = JSON.stringify(localEntries)
      saveRecord(activeRecordId, content)
    }, AUTOSAVE_DEBOUNCE_MS)
  }, [activeRecordId, localEntries, saveRecord])

  useEffect(() => {
    return () => {
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current)
    }
  }, [])

  const handleEntryChange = useCallback((entryId: string, newContent: string) => {
    setLocalEntries((prev) =>
      prev.map((e) => (e.id === entryId ? { ...e, content: newContent } : e))
    )
    triggerSave()
  }, [triggerSave])

  const handleAddEntry = useCallback((type: EntryType) => {
    const newEntry: RecordEntry = {
      id: crypto.randomUUID(),
      type,
      content: '',
      createdAt: new Date().toISOString(),
    }
    setLocalEntries((prev) => [...prev, newEntry])
    triggerSave()
    // Focus the new entry if text
    if (type === 'text') {
      setTimeout(() => {
        textareaRefs.current.get(newEntry.id)?.focus()
      }, 50)
    }
  }, [triggerSave])

  const handleRemoveEntry = useCallback((entryId: string) => {
    setLocalEntries((prev) => prev.filter((e) => e.id !== entryId))
    triggerSave()
  }, [triggerSave])

  const handleBreadcrumbFolderClick = useCallback(() => {
    if (activeFolder) {
      toggleFolderExpanded(activeFolder.id)
    }
  }, [activeFolder, toggleFolderExpanded])

  const handleRetry = useCallback(() => {
    setError(false)
    if (activeRecordId) {
      useWorkspaceStore.getState().setActiveRecord(null)
      setTimeout(() => {
        useWorkspaceStore.getState().setActiveRecord(activeRecordId)
      }, 50)
    }
  }, [activeRecordId])

  const truncatedTitle = useMemo(() => {
    if (!activeRecord) return ''
    return activeRecord.title.length > BREADCRUMB_MAX_TITLE_LENGTH
      ? activeRecord.title.slice(0, BREADCRUMB_MAX_TITLE_LENGTH) + '…'
      : activeRecord.title
  }, [activeRecord])

  // Empty state
  if (!activeRecordId) {
    return <InsightsFeed />
  }

  // Error state
  if (error) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3">
        <p className="text-sm text-zinc-400">Record not found</p>
        <button
          type="button"
          onClick={handleRetry}
          className={clsx(
            'rounded-md border border-[#3ecf8e]/40 px-3 py-1.5 text-sm font-medium',
            'text-[#3ecf8e] transition-colors',
            'hover:border-[#3ecf8e] hover:bg-[#3ecf8e]/10',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3ecf8e]/60'
          )}
        >
          Retry
        </button>
      </div>
    )
  }

  return (
    <div
      className={clsx(
        'flex h-full flex-col',
        !prefersReducedMotion.current && 'transition-opacity duration-300',
        transitioning ? 'opacity-0' : 'opacity-100'
      )}
    >
      {/* Breadcrumb + inline input type buttons */}
      {activeFolder && activeRecord && (
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-1 text-sm">
            <button
              type="button"
              onClick={handleBreadcrumbFolderClick}
              className={clsx(
                'truncate rounded px-1 py-0.5 text-zinc-500 transition-colors',
                'hover:text-zinc-300',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3ecf8e]/60'
              )}
            >
              {activeFolder.name}
            </button>
            <ChevronRight size={12} className="shrink-0 text-zinc-600" />
            <span className="truncate text-zinc-200">{truncatedTitle}</span>
          </div>
          {/* Input type buttons + close button — top right */}
          <div className="flex items-center gap-1.5">
            {ENTRY_TYPE_ICONS.map(({ type, label, icon: Icon }) => (
              <button
                key={type}
                type="button"
                onClick={() => handleAddEntry(type)}
                className={clsx(
                  'flex items-center gap-1 rounded-md px-2 py-1 transition-all duration-150',
                  'border border-dashed border-zinc-700 text-zinc-500',
                  'hover:border-zinc-500 hover:text-zinc-200 hover:bg-white/5',
                  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3ecf8e]/60'
                )}
                aria-label={`Add ${label}`}
              >
                <Icon size={12} />
                <span className="text-[10px] font-medium">{label}</span>
              </button>
            ))}
            <button
              type="button"
              onClick={() => useWorkspaceStore.getState().setActiveRecord(null)}
              aria-label="Close record"
              className={clsx(
                'flex items-center gap-1 rounded-md px-2 py-1 transition-all duration-150',
                'border border-zinc-700 text-zinc-500',
                'hover:border-red-500/50 hover:text-red-400 hover:bg-red-500/5',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500/60'
              )}
            >
              <X size={12} />
              <span className="text-[10px] font-medium">Close</span>
            </button>
          </div>
        </div>
      )}

      {/* Entries column layout */}
      <div className="flex-1 overflow-y-auto space-y-3 pb-4">
        {localEntries.length === 0 && (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <p className="text-sm text-zinc-500 mb-3">Add content to this record</p>
            <p className="text-xs text-zinc-600">Choose an input type below</p>
          </div>
        )}

        {localEntries.map((entry) => (
          <div
            key={entry.id}
            className="group relative rounded-lg border border-white/5 bg-[#0f0f0f] p-3"
          >
            {/* Remove button */}
            <button
              type="button"
              onClick={() => handleRemoveEntry(entry.id)}
              className={clsx(
                'absolute right-2 top-2 rounded p-1 text-zinc-600 opacity-0',
                'transition-opacity group-hover:opacity-100',
                'hover:bg-white/10 hover:text-zinc-300'
              )}
              aria-label="Remove entry"
            >
              <X size={12} />
            </button>

            {/* Entry type indicator */}
            <div className="mb-2 flex items-center gap-1.5">
              {entry.type === 'text' && <Type size={12} className="text-zinc-500" />}
              {entry.type === 'image' && <Image size={12} className="text-zinc-500" />}
              {entry.type === 'audio' && <Mic size={12} className="text-zinc-500" />}
              {entry.type === 'pdf' && <FileText size={12} className="text-zinc-500" />}
              <span className="text-[10px] uppercase tracking-wide text-zinc-600">
                {entry.type}
              </span>
            </div>

            {/* Entry content */}
            {entry.type === 'text' && (
              <textarea
                ref={(el) => {
                  if (el) textareaRefs.current.set(entry.id, el)
                  else textareaRefs.current.delete(entry.id)
                }}
                value={entry.content}
                onChange={(e) => handleEntryChange(entry.id, e.target.value)}
                placeholder="Type something..."
                className={clsx(
                  'w-full min-h-[60px] resize-none bg-transparent text-sm leading-relaxed',
                  'text-zinc-200 placeholder-zinc-600',
                  'focus:outline-none'
                )}
              />
            )}

            {entry.type === 'image' && (
              <div className="flex items-center justify-center rounded-md border border-dashed border-zinc-700 py-6">
                {entry.content ? (
                  <img src={entry.content} alt="" className="max-h-48 rounded" />
                ) : (
                  <label className="cursor-pointer text-xs text-zinc-500 hover:text-zinc-300">
                    Click to upload image
                    <input
                      type="file"
                      accept="image/*"
                      className="hidden"
                      onChange={(e) => {
                        const file = e.target.files?.[0]
                        if (file) {
                          const url = URL.createObjectURL(file)
                          handleEntryChange(entry.id, url)
                        }
                      }}
                    />
                  </label>
                )}
              </div>
            )}

            {entry.type === 'audio' && (
              <div className="flex items-center justify-center rounded-md border border-dashed border-zinc-700 py-6">
                {entry.content ? (
                  <audio controls src={entry.content} className="w-full max-w-xs" />
                ) : (
                  <label className="cursor-pointer text-xs text-zinc-500 hover:text-zinc-300">
                    Click to upload audio
                    <input
                      type="file"
                      accept="audio/*"
                      className="hidden"
                      onChange={(e) => {
                        const file = e.target.files?.[0]
                        if (file) {
                          const url = URL.createObjectURL(file)
                          handleEntryChange(entry.id, url)
                        }
                      }}
                    />
                  </label>
                )}
              </div>
            )}

            {entry.type === 'pdf' && (
              <div className="flex items-center justify-center rounded-md border border-dashed border-zinc-700 py-6">
                {entry.content ? (
                  <a href={entry.content} target="_blank" rel="noopener noreferrer" className="text-xs text-[#3ecf8e] hover:underline">
                    View PDF
                  </a>
                ) : (
                  <label className="cursor-pointer text-xs text-zinc-500 hover:text-zinc-300">
                    Click to upload PDF
                    <input
                      type="file"
                      accept=".pdf"
                      className="hidden"
                      onChange={(e) => {
                        const file = e.target.files?.[0]
                        if (file) {
                          const url = URL.createObjectURL(file)
                          handleEntryChange(entry.id, url)
                        }
                      }}
                    />
                  </label>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

    </div>
  )
}
