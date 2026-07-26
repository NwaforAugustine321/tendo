import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Plus, Search, Filter, MoreVertical, Folder, Briefcase, Wallet, ShoppingBag, Users, FileText, Archive, Star, Heart, Zap, Globe, Code } from 'lucide-react'
import clsx from 'clsx'
import { FolderItem, RecordItem, RecordActionBar, MovePanel, ContextMenu } from '../atoms'
import { useWorkspaceStore } from '../../store/workspace'
import { filterByQuery } from '../../lib/workspace/search-utils'
import { SEARCH_DEBOUNCE_MS, FOLDER_ICONS_LIST } from '../../lib/workspace/constants'
import type { Folder as FolderType, FolderIcon, Record as WorkspaceRecord, ContextMenuState } from '../../lib/workspace/types'
import * as recordsApi from '../../lib/services/records'
import { toast } from 'sonner'

const ICON_PICKER_MAP: { [key in FolderIcon]: typeof Folder } = {
  'folder': Folder,
  'briefcase': Briefcase,
  'wallet': Wallet,
  'shopping-bag': ShoppingBag,
  'users': Users,
  'file-text': FileText,
  'archive': Archive,
  'star': Star,
  'heart': Heart,
  'zap': Zap,
  'globe': Globe,
  'code': Code,
}

type Props = {
  onRecordSelect?: (recordId: string) => void
}

export function FolderNavigation({ onRecordSelect }: Props) {
  const {
    folders,
    records,
    expandedFolderIds,
    searchQuery,
    contextMenu,
    dragState,
    toggleFolderExpanded,
    createFolder,
    createRecord,
    moveRecord,
    deleteRecord,
    renameRecord,
    setActiveRecord,
    setActiveFolderId,
    setDragState,
    setContextMenu,
    setSearchQuery,
  } = useWorkspaceStore()

  const foldersLoading = useWorkspaceStore((s) => s.foldersLoading)
  const recordsLoading = useWorkspaceStore((s) => s.recordsLoading)

  const [localQuery, setLocalQuery] = useState(searchQuery)
  const [creatingFolder, setCreatingFolder] = useState(false)
  const [newFolderName, setNewFolderName] = useState('')
  const [newFolderIcon, setNewFolderIcon] = useState<FolderIcon>('folder')
  const [actionBar, setActionBar] = useState<{
    recordId: string
    folderId: string
    position: { x: number; y: number }
  } | null>(null)
  const [movePanel, setMovePanel] = useState<{
    recordId: string
    folderId: string
  } | null>(null)
  const [renamingRecord, setRenamingRecord] = useState<{
    recordId: string
    folderId: string
    currentName: string
  } | null>(null)
  const [renamingFolder, setRenamingFolder] = useState<{
    folderId: string
    currentName: string
  } | null>(null)
  const [dragOverFolderId, setDragOverFolderId] = useState<string | null>(null)

  const newFolderInputRef = useRef<HTMLInputElement>(null)
  const renameInputRef = useRef<HTMLInputElement>(null)
  const renameFolderInputRef = useRef<HTMLInputElement>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const folderListRef = useRef<HTMLDivElement>(null)

  // Debounced search
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      setSearchQuery(localQuery)
    }, SEARCH_DEBOUNCE_MS)
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [localQuery, setSearchQuery])

  // Auto-focus new folder input
  useEffect(() => {
    if (creatingFolder) {
      newFolderInputRef.current?.focus()
    }
  }, [creatingFolder])

  // Auto-focus rename input
  useEffect(() => {
    if (renamingRecord) {
      renameInputRef.current?.focus()
      renameInputRef.current?.select()
    }
  }, [renamingRecord])

  useEffect(() => {
    if (renamingFolder) {
      renameFolderInputRef.current?.focus()
      renameFolderInputRef.current?.select()
    }
  }, [renamingFolder])

  // Filter folders by search
  const filteredFolders = useMemo(
    () => filterByQuery(folders, searchQuery, (f) => f.name),
    [folders, searchQuery]
  )

  // Check if any records match search within a folder
  const getFilteredRecords = useCallback(
    (folderId: string): WorkspaceRecord[] => {
      const folderRecords = records.get(folderId) || []
      if (!searchQuery.trim()) return folderRecords
      return filterByQuery(folderRecords, searchQuery, (r) => r.title)
    },
    [records, searchQuery]
  )

  // Filter: show folders that match OR have matching records
  const visibleFolders = useMemo(() => {
    if (!searchQuery.trim()) return filteredFolders
    return folders.filter((f) => {
      const nameMatch = f.name.toLowerCase().includes(searchQuery.toLowerCase())
      const folderRecords = records.get(f.id) || []
      const recordMatch = folderRecords.some((r) =>
        r.title.toLowerCase().includes(searchQuery.toLowerCase())
      )
      return nameMatch || recordMatch
    })
  }, [folders, filteredFolders, records, searchQuery])

  const handleNewFolderSave = useCallback(() => {
    const trimmed = newFolderName.trim()
    if (trimmed) {
      createFolder(trimmed, newFolderIcon)
    }
    setCreatingFolder(false)
    setNewFolderName('')
    setNewFolderIcon('folder')
  }, [newFolderName, newFolderIcon, createFolder])

  const handleNewFolderKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter') {
        handleNewFolderSave()
      } else if (e.key === 'Escape') {
        setCreatingFolder(false)
        setNewFolderName('')
        setNewFolderIcon('folder')
      }
    },
    [handleNewFolderSave]
  )

  const handleRecordSelect = useCallback(
    (recordId: string, folderId: string) => {
      setActiveRecord(recordId)
      setActiveFolderId(folderId)
      onRecordSelect?.(recordId)
    },
    [setActiveRecord, setActiveFolderId, onRecordSelect]
  )

  const handleRecordMenuClick = useCallback(
    (e: React.MouseEvent, recordId: string, folderId: string) => {
      setActionBar({
        recordId,
        folderId,
        position: { x: e.clientX, y: e.clientY },
      })
    },
    []
  )

  const handleActionBarAction = useCallback(
    (action: 'move' | 'organise' | 'rename' | 'delete') => {
      if (!actionBar) return

      switch (action) {
        case 'organise':
          setMovePanel({ recordId: actionBar.recordId, folderId: actionBar.folderId })
          setActionBar(null)
          break
        case 'rename': {
          const folderRecords = records.get(actionBar.folderId) || []
          const record = folderRecords.find((r) => r.id === actionBar.recordId)
          if (record) {
            setRenamingRecord({
              recordId: actionBar.recordId,
              folderId: actionBar.folderId,
              currentName: record.title,
            })
          }
          setActionBar(null)
          break
        }
        case 'delete':
          deleteRecord(actionBar.recordId, actionBar.folderId)
          toast.promise(recordsApi.deleteRecord(actionBar.recordId), { loading: "Deleting record...", success: "Record deleted", error: "Failed to delete record" })
          setActionBar(null)
          break
        default:
          setActionBar(null)
          break
      }
    },
    [actionBar, records, deleteRecord]
  )

  const handleMoveToFolder = useCallback(
    (targetFolderId: string) => {
      if (!movePanel) return
      moveRecord(movePanel.recordId, movePanel.folderId, targetFolderId)
      recordsApi.moveRecord(movePanel.recordId, targetFolderId).then(() => toast.success("Record moved")).catch(() => toast.error("Failed to move record"))
      setMovePanel(null)
    },
    [movePanel, moveRecord]
  )

  const handleRenameSave = useCallback(() => {
    if (!renamingRecord) return
    renameRecord(renamingRecord.recordId, renamingRecord.folderId, renamingRecord.currentName)
    recordsApi.updateRecord(renamingRecord.recordId, renamingRecord.currentName).then(() => toast.success("Record renamed")).catch(() => toast.error("Failed to rename record"))
    setRenamingRecord(null)
  }, [renamingRecord, renameRecord])

  const handleRenameKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      e.stopPropagation()
      if (e.key === 'Enter') {
        handleRenameSave()
      } else if (e.key === 'Escape') {
        setRenamingRecord(null)
      }
    },
    [handleRenameSave]
  )

  // Drag and drop
  const handleDragStart = useCallback(
    (e: React.DragEvent, recordId: string, folderId: string) => {
      e.dataTransfer.effectAllowed = 'move'
      e.dataTransfer.setData('text/plain', recordId)
      setDragState({ recordId, sourceFolderId: folderId, currentTargetFolderId: null })
    },
    [setDragState]
  )

  const handleDragOver = useCallback(
    (e: React.DragEvent, folderId: string) => {
      e.preventDefault()
      e.dataTransfer.dropEffect = 'move'
      setDragOverFolderId(folderId)
    },
    []
  )

  const handleDragLeave = useCallback(() => {
    setDragOverFolderId(null)
  }, [])

  const handleDrop = useCallback(
    (e: React.DragEvent, targetFolderId: string) => {
      e.preventDefault()
      setDragOverFolderId(null)
      if (dragState) {
        moveRecord(dragState.recordId, dragState.sourceFolderId, targetFolderId)
        setDragState(null)
      }
    },
    [dragState, moveRecord, setDragState]
  )

  // Context menu for folders and records
  const handleFolderContextMenu = useCallback(
    (e: React.MouseEvent, folder: FolderType) => {
      e.preventDefault()
      setContextMenu({
        target: { type: 'folder', folderId: folder.id },
        position: { x: e.clientX, y: e.clientY },
      })
    },
    [setContextMenu]
  )

  const handleRecordContextMenu = useCallback(
    (e: React.MouseEvent, recordId: string, folderId: string) => {
      e.preventDefault()
      setContextMenu({
        target: { type: 'record', recordId, folderId },
        position: { x: e.clientX, y: e.clientY },
      })
    },
    [setContextMenu]
  )

  const getContextMenuItems = useCallback(
    (state: ContextMenuState) => {
      if (state.target.type === 'folder') {
        const folderId = state.target.folderId
        return [
          {
            label: 'New Record',
            onClick: () => createRecord(folderId, 'note'),
          },
          {
            label: 'Rename Folder',
            onClick: () => {
              const folder = folders.find((f) => f.id === folderId)
              if (folder) {
                setRenamingFolder({ folderId, currentName: folder.name })
              }
            },
          },
          {
            label: 'Delete Folder',
            onClick: () => {
              useWorkspaceStore.getState().deleteFolder(folderId)
              toast.promise(recordsApi.deleteFolder(folderId), { loading: "Deleting folder...", success: "Folder deleted", error: "Failed to delete folder" })
            },
            danger: true,
          },
        ]
      }
      const { recordId, folderId } = state.target
      return [
        {
          label: 'Rename',
          onClick: () => {
            const folderRecords = records.get(folderId) || []
            const record = folderRecords.find((r) => r.id === recordId)
            if (record) {
              setRenamingRecord({ recordId, folderId, currentName: record.title })
            }
          },
        },
        {
          label: 'Organise',
          onClick: () => setMovePanel({ recordId, folderId }),
        },
        {
          label: 'Delete',
          onClick: () => {
            deleteRecord(recordId, folderId)
            toast.promise(recordsApi.deleteRecord(recordId), { loading: "Deleting record...", success: "Record deleted", error: "Failed to delete record" })
          },
          danger: true,
        },
      ]
    },
    [createRecord, deleteRecord, records, folders]
  )

  // Keyboard navigation
  const handleListKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        e.preventDefault()
        const items = folderListRef.current?.querySelectorAll<HTMLElement>(
          '[data-folder-nav-item]'
        )
        if (!items || items.length === 0) return

        const current = document.activeElement as HTMLElement
        const currentIndex = Array.from(items).indexOf(current)
        const nextIndex =
          e.key === 'ArrowDown'
            ? Math.min(currentIndex + 1, items.length - 1)
            : Math.max(currentIndex - 1, 0)
        items[nextIndex]?.focus()
      }
    },
    []
  )

  return (
    <div className="flex h-full flex-col bg-[#0f0f0f]">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-3">
        <h2 className="text-sm font-semibold text-zinc-200">My Space</h2>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => setCreatingFolder(true)}
            className={clsx(
              'flex items-center gap-1 rounded px-2 py-1 text-xs font-medium',
              'text-[#3ecf8e] transition-colors',
              'hover:bg-[#3ecf8e]/10',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3ecf8e]/60'
            )}
          >
            <Plus size={12} />
            New Folder
          </button>
          <button
            type="button"
            aria-label="More options"
            className={clsx(
              'flex h-7 w-7 items-center justify-center rounded text-zinc-500',
              'transition-colors hover:bg-white/5 hover:text-zinc-300',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3ecf8e]/60'
            )}
          >
            <MoreVertical size={14} />
          </button>
        </div>
      </div>

      {/* Search with filter button */}
      <div className="px-3 pb-2">
        <div className="flex items-center gap-2">
          <div className="relative flex-1">
            <Search
              size={14}
              className="absolute left-2.5 top-1/2 -translate-y-1/2 text-zinc-500"
            />
            <input
              type="text"
              value={localQuery}
              onChange={(e) => setLocalQuery(e.target.value)}
              placeholder="Search folders or records..."
              aria-label="Search folders and records"
              className={clsx(
                'w-full rounded-lg border border-white/10 bg-[#161616] py-2 pl-8 pr-3',
                'text-sm text-zinc-300 placeholder-zinc-600',
                'transition-colors focus:border-[#3ecf8e]/40 focus:outline-none'
              )}
            />
          </div>
          <button
            type="button"
            aria-label="Filter"
            className={clsx(
              'flex h-[36px] w-[36px] shrink-0 items-center justify-center rounded-lg',
              'border border-white/10 bg-[#161616] text-zinc-500',
              'transition-colors hover:border-white/20 hover:text-zinc-300',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3ecf8e]/60'
            )}
          >
            <Filter size={14} />
          </button>
        </div>
      </div>

      {/* New folder creation with icon picker */}
      {creatingFolder && (
        <div className="px-3 pb-2 space-y-2">
          {/* Icon picker row */}
          <div className="flex flex-wrap gap-1">
            {FOLDER_ICONS_LIST.map((iconKey) => {
              const IconComp = ICON_PICKER_MAP[iconKey]
              return (
                <button
                  key={iconKey}
                  type="button"
                  onClick={() => setNewFolderIcon(iconKey)}
                  aria-label={`Select ${iconKey} icon`}
                  className={clsx(
                    'flex h-7 w-7 items-center justify-center rounded transition-colors',
                    newFolderIcon === iconKey
                      ? 'bg-[#3ecf8e]/20 text-[#3ecf8e] border border-[#3ecf8e]/40'
                      : 'text-zinc-500 hover:bg-white/5 hover:text-zinc-300 border border-transparent'
                  )}
                >
                  <IconComp size={14} />
                </button>
              )
            })}
          </div>
          {/* Name input */}
          <input
            ref={newFolderInputRef}
            type="text"
            value={newFolderName}
            onChange={(e) => setNewFolderName(e.target.value)}
            onBlur={handleNewFolderSave}
            onKeyDown={handleNewFolderKeyDown}
            placeholder="Folder name..."
            aria-label="New folder name"
            className={clsx(
              'w-full rounded-lg border border-[#3ecf8e]/40 bg-[#0a0a0a] px-3 py-2',
              'text-sm text-zinc-200 placeholder-zinc-600',
              'focus:border-[#3ecf8e] focus:outline-none'
            )}
          />
        </div>
      )}

      {/* Folder list */}
      <div
        ref={folderListRef}
        className="flex-1 overflow-y-auto px-2 py-1"
        onKeyDown={handleListKeyDown}
      >
        {visibleFolders.length === 0 && searchQuery.trim() ? (
          <div className="px-3 py-8 text-center">
            <p className="text-sm text-zinc-500">No results found</p>
          </div>
        ) : foldersLoading ? (
          <div className="px-3 py-8 text-center">
            <p className="text-xs text-zinc-500 animate-pulse">Loading folders...</p>
          </div>
        ) : (
          <div className="space-y-1">
            {visibleFolders.map((folder) => {
              const isExpanded = expandedFolderIds.has(folder.id)
              const folderRecords = getFilteredRecords(folder.id)
              const isDragOver = dragOverFolderId === folder.id

              return (
                <div
                  key={folder.id}
                  data-folder-nav-item
                  onDragOver={(e) => handleDragOver(e, folder.id)}
                  onDragLeave={handleDragLeave}
                  onDrop={(e) => handleDrop(e, folder.id)}
                  className={clsx(
                    'rounded-lg transition-all duration-150',
                    isDragOver && 'border border-[#3ecf8e]/50 bg-[#3ecf8e]/5'
                  )}
                >
                  <FolderItem
                    folder={folder}
                    isExpanded={isExpanded}
                    onToggle={() => {
                      toggleFolderExpanded(folder.id)
                      if (!expandedFolderIds.has(folder.id)) {
                        useWorkspaceStore.getState().fetchRecords(folder.id)
                      }
                    }}
                    onContextMenu={(e) => handleFolderContextMenu(e, folder)}
                    renaming={renamingFolder?.folderId === folder.id ? {
                      name: renamingFolder.currentName,
                      onChange: (name) => setRenamingFolder((prev) => prev ? { ...prev, currentName: name } : prev),
                      onSave: () => {
                        if (renamingFolder.currentName.trim()) {
                          useWorkspaceStore.getState().renameFolder(folder.id, renamingFolder.currentName.trim())
                          recordsApi.updateFolder(folder.id, renamingFolder.currentName.trim(), folder.icon, folder.color).then(() => toast.success("Folder renamed")).catch(() => toast.error("Failed to rename folder"))
                        }
                        setRenamingFolder(null)
                      },
                      onCancel: () => setRenamingFolder(null),
                    } : undefined}
                  >
                    {recordsLoading.get(folder.id) ? (
                      <p className="px-2 py-2 text-xs text-zinc-500 animate-pulse">Loading records...</p>
                    ) : folderRecords.map((record) => (
                      <div key={record.id}>
                        {renamingRecord?.recordId === record.id ? (
                          <div className="px-2 py-1">
                            <input
                              ref={renameInputRef}
                              type="text"
                              defaultValue={renamingRecord.currentName}
                              onBlur={(e) => {
                                const val = e.target.value.trim()
                                if (val) {
                                  renameRecord(renamingRecord.recordId, renamingRecord.folderId, val)
                                  recordsApi.updateRecord(renamingRecord.recordId, val).then(() => toast.success("Record renamed")).catch(() => toast.error("Failed to rename record"))
                                }
                                setRenamingRecord(null)
                              }}
                              onKeyDown={(e) => {
                                e.stopPropagation()
                                if (e.key === 'Enter') {
                                  (e.target as HTMLInputElement).blur()
                                } else if (e.key === 'Escape') {
                                  setRenamingRecord(null)
                                }
                              }}
                              autoComplete="off"
                              className={clsx(
                                'w-full rounded border border-[#3ecf8e]/40 bg-[#0a0a0a] px-2 py-1',
                                'text-sm text-zinc-200 focus:border-[#3ecf8e] focus:outline-none'
                              )}
                            />
                          </div>
                        ) : (
                          <RecordItem
                            record={record}
                            onSelect={() => handleRecordSelect(record.id, folder.id)}
                            onMenuClick={(e) => handleRecordMenuClick(e, record.id, folder.id)}
                            onDragStart={(e) => handleDragStart(e, record.id, folder.id)}
                            onContextMenu={(e) =>
                              handleRecordContextMenu(e, record.id, folder.id)
                            }
                          />
                        )}
                        {/* Move panel shown inline below the record */}
                        {movePanel?.recordId === record.id && (
                          <div className="ml-4 mt-1 mb-1">
                            <MovePanel
                              folders={folders}
                              excludeFolderId={folder.id}
                              onMoveToFolder={handleMoveToFolder}
                              onClose={() => setMovePanel(null)}
                            />
                          </div>
                        )}
                      </div>
                    ))}
                    {/* New record link in expanded folder */}
                    {isExpanded && (
                      <button
                        type="button"
                        onClick={() => createRecord(folder.id, 'note')}
                        className={clsx(
                          'mt-1 flex w-full items-center gap-1.5 rounded-md border border-dashed border-zinc-600 px-2 py-1.5',
                          'text-xs font-medium text-white transition-colors',
                          'hover:border-zinc-400 hover:bg-white/5'
                        )}
                      >
                        <Plus size={12} />
                        <span>New Record in {folder.name}</span>
                      </button>
                    )}
                  </FolderItem>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Bottom new folder link */}
      <div className="border-t border-white/5 px-3 py-2.5">
        <button
          type="button"
          onClick={() => setCreatingFolder(true)}
          className={clsx(
            'flex w-full items-center justify-center gap-1.5 rounded-md py-1.5',
            'text-xs font-medium text-[#3ecf8e] transition-colors',
            'hover:bg-[#3ecf8e]/10'
          )}
        >
          <Plus size={12} />
          New Folder
        </button>
      </div>

      {/* Record action bar */}
      {actionBar && (
        <RecordActionBar
          position={actionBar.position}
          onAction={handleActionBarAction}
          onClose={() => setActionBar(null)}
        />
      )}

      {/* Context menu */}
      {contextMenu && (
        <ContextMenu
          position={contextMenu.position}
          items={getContextMenuItems(contextMenu)}
          onClose={() => setContextMenu(null)}
        />
      )}
    </div>
  )
}
