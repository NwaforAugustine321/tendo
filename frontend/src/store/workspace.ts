import { create } from 'zustand'
import { toast } from 'sonner'
import type {
  Folder,
  FolderIcon,
  Record,
  RecordType,
  RadialViewState,
  DragState,
  ContextMenuState,
} from '../lib/workspace/types'
import {
  normalizeFolderName,
  generateUniqueName,
  getNextFolderColor,
} from '../lib/workspace/folder-utils'
import * as recordsApi from '../lib/services/records'

export interface WorkspaceState {
  // Folder state
  folders: Folder[]
  expandedFolderIds: Set<string>
  activeFolderId: string | null

  // Record state
  records: Map<string, Record[]> // folderId -> records
  activeRecordId: string | null

  // Radial menu state
  radialMenuOpen: boolean
  radialMenuView: RadialViewState

  // Drag state
  dragState: DragState | null

  // Context menu state
  contextMenu: ContextMenuState | null

  // Search
  searchQuery: string

  // Loading
  foldersLoading: boolean
  recordsLoading: Map<string, boolean>

  // Actions — radial menu
  openRadialMenu: () => void
  closeRadialMenu: () => void
  setRadialView: (view: RadialViewState) => void

  // Actions — folders
  createFolder: (name: string, icon?: FolderIcon) => void
  renameFolder: (folderId: string, name: string) => void
  deleteFolder: (folderId: string) => void

  // Actions — records
  createRecord: (folderId: string, type: RecordType, title?: string) => void
  moveRecord: (recordId: string, sourceFolderId: string, targetFolderId: string) => void
  renameRecord: (recordId: string, folderId: string, name: string) => void
  deleteRecord: (recordId: string, folderId: string) => void

  // Actions — UI state
  toggleFolderExpanded: (folderId: string) => void
  setActiveRecord: (recordId: string | null) => void
  setActiveFolderId: (folderId: string | null) => void
  setDragState: (state: DragState | null) => void
  setContextMenu: (state: ContextMenuState | null) => void
  setSearchQuery: (query: string) => void

  // Async actions (API)
  fetchFolders: () => Promise<void>
  fetchRecords: (folderId: string) => Promise<void>
  saveRecord: (recordId: string, content: string) => Promise<void>
}

export const useWorkspaceStore = create<WorkspaceState>((set, get) => ({
  folders: [],
  expandedFolderIds: new Set(),
  activeFolderId: null,

  records: new Map(),
  activeRecordId: null,

  radialMenuOpen: false,
  radialMenuView: { view: 'actions' },

  dragState: null,
  contextMenu: null,
  searchQuery: '',
  foldersLoading: false,
  recordsLoading: new Map(),

  // Radial menu
  openRadialMenu: () => set({ radialMenuOpen: true, radialMenuView: { view: 'actions' } }),
  closeRadialMenu: () => set({ radialMenuOpen: false, radialMenuView: { view: 'actions' } }),
  setRadialView: (view) => set({ radialMenuView: view }),

  // Folders
  createFolder: (name, icon) => {
    const { folders } = get()
    const existingNames = folders.map((f) => f.name)
    const uniqueName = generateUniqueName(name, existingNames)
    const color = getNextFolderColor(folders)
    const now = new Date().toISOString()

    const tempId = crypto.randomUUID()
    const newFolder: Folder = {
      id: tempId,
      name: uniqueName,
      color,
      icon: icon || 'folder',
      recordCount: 0,
      createdAt: now,
      updatedAt: now,
    }

    set({ folders: [...folders, newFolder] })

    recordsApi.createFolder(uniqueName, icon || 'folder', color).then((apiFolder) => {
      const { folders: current } = get()
      set({ folders: current.map((f) => f.id === tempId ? { ...f, id: apiFolder.id } : f) })
      toast.success('Folder created')
    }).catch(() => { toast.error('Failed to create folder') })
  },

  renameFolder: (folderId, name) => {
    const { folders } = get()
    const normalized = normalizeFolderName(name)
    const otherNames = folders.filter((f) => f.id !== folderId).map((f) => f.name)
    const uniqueName = otherNames.includes(normalized)
      ? generateUniqueName(normalized, otherNames)
      : normalized

    set({
      folders: folders.map((f) =>
        f.id === folderId ? { ...f, name: uniqueName, updatedAt: new Date().toISOString() } : f
      ),
    })
  },

  deleteFolder: (folderId) => {
    const { folders, records, activeRecordId, activeFolderId } = get()
    const newRecords = new Map(records)
    newRecords.delete(folderId)

    // If active record was in deleted folder, clear it
    const deletedRecords = records.get(folderId) || []
    const newActiveRecord = deletedRecords.some((r) => r.id === activeRecordId)
      ? null
      : activeRecordId

    set({
      folders: folders.filter((f) => f.id !== folderId),
      records: newRecords,
      activeRecordId: newActiveRecord,
      activeFolderId: activeFolderId === folderId ? null : activeFolderId,
    })
  },

  // Records
  createRecord: (folderId, type, title) => {
    const { records, folders } = get()
    const now = new Date().toISOString()
    const tempId = crypto.randomUUID()
    const newRecord: Record = {
      id: tempId,
      folderId,
      title: title || 'Untitled',
      content: '',
      entries: [],
      type,
      createdAt: now,
      updatedAt: now,
    }

    const folderRecords = records.get(folderId) || []
    const newRecords = new Map(records)
    newRecords.set(folderId, [...folderRecords, newRecord])

    set({
      records: newRecords,
      activeRecordId: tempId,
      activeFolderId: folderId,
      folders: folders.map((f) =>
        f.id === folderId ? { ...f, recordCount: f.recordCount + 1 } : f
      ),
    })

    recordsApi.createRecord(folderId, title || 'Untitled').then((apiRecord) => {
      const { records: current } = get()
      const newRecs = new Map(current)
      const folderRecs = newRecs.get(folderId) || []
      newRecs.set(folderId, folderRecs.map((r) => r.id === tempId ? { ...r, id: apiRecord.id } : r))
      set({ records: newRecs, activeRecordId: apiRecord.id })
      toast.success('Record created')
    }).catch(() => { toast.error('Failed to create record') })
  },

  moveRecord: (recordId, sourceFolderId, targetFolderId) => {
    if (sourceFolderId === targetFolderId) return

    const { records, folders } = get()
    const sourceRecords = records.get(sourceFolderId) || []
    const targetRecords = records.get(targetFolderId) || []
    const record = sourceRecords.find((r) => r.id === recordId)
    if (!record) return

    const movedRecord = { ...record, folderId: targetFolderId, updatedAt: new Date().toISOString() }
    const newRecords = new Map(records)
    newRecords.set(
      sourceFolderId,
      sourceRecords.filter((r) => r.id !== recordId)
    )
    newRecords.set(targetFolderId, [...targetRecords, movedRecord])

    set({
      records: newRecords,
      folders: folders.map((f) => {
        if (f.id === sourceFolderId) return { ...f, recordCount: f.recordCount - 1 }
        if (f.id === targetFolderId) return { ...f, recordCount: f.recordCount + 1 }
        return f
      }),
    })
  },

  renameRecord: (recordId, folderId, name) => {
    const { records } = get()
    const folderRecords = records.get(folderId) || []
    const trimmed = name.trim() || 'Untitled'

    const newRecords = new Map(records)
    newRecords.set(
      folderId,
      folderRecords.map((r) =>
        r.id === recordId ? { ...r, title: trimmed.slice(0, 100), updatedAt: new Date().toISOString() } : r
      )
    )
    set({ records: newRecords })
  },

  deleteRecord: (recordId, folderId) => {
    const { records, folders, activeRecordId } = get()
    const folderRecords = records.get(folderId) || []

    const newRecords = new Map(records)
    newRecords.set(
      folderId,
      folderRecords.filter((r) => r.id !== recordId)
    )

    set({
      records: newRecords,
      activeRecordId: activeRecordId === recordId ? null : activeRecordId,
      folders: folders.map((f) =>
        f.id === folderId ? { ...f, recordCount: Math.max(0, f.recordCount - 1) } : f
      ),
    })
  },

  // UI state
  toggleFolderExpanded: (folderId) => {
    const { expandedFolderIds } = get()
    const newSet = new Set(expandedFolderIds)
    if (newSet.has(folderId)) {
      newSet.delete(folderId)
    } else {
      newSet.add(folderId)
    }
    set({ expandedFolderIds: newSet })
  },

  setActiveRecord: (recordId) => set({ activeRecordId: recordId }),
  setActiveFolderId: (folderId) => set({ activeFolderId: folderId }),
  setDragState: (state) => set({ dragState: state }),
  setContextMenu: (state) => set({ contextMenu: state }),
  setSearchQuery: (query) => set({ searchQuery: query }),

  // Async — API integration
  fetchFolders: async () => {
    set({ foldersLoading: true })
    try {
      const apiFolders = await recordsApi.getFolders()
      console.log('[workspace] fetchFolders response:', apiFolders)
      const folders: Folder[] = apiFolders.map((f: any) => ({
        id: f.id,
        name: f.name,
        color: (f.color || 'blue') as any,
        icon: (f.icon || 'folder') as any,
        recordCount: f.record_count || 0,
        createdAt: f.created_at,
        updatedAt: f.updated_at,
      }))

      const newRecords = new Map<string, Record[]>()
      for (const f of apiFolders) {
        const folderRecords = (f.records || []).map((r: any) => ({
          id: r.id,
          folderId: f.id,
          title: r.title,
          content: '',
          entries: [],
          type: 'note' as RecordType,
          createdAt: r.created_at,
          updatedAt: r.updated_at,
        }))
        newRecords.set(f.id, folderRecords)
      }

      set({ folders, records: newRecords, foldersLoading: false })
    } catch {
      set({ foldersLoading: false })
    }
  },
  fetchRecords: async (folderId) => {
    const { recordsLoading } = get()
    const newLoading = new Map(recordsLoading)
    newLoading.set(folderId, true)
    set({ recordsLoading: newLoading })
    try {
      const apiRecords = await recordsApi.getRecords(folderId)
      const records = get().records
      const newRecords = new Map(records)
      newRecords.set(folderId, apiRecords.map((r) => ({
        id: r.id,
        folderId: r.folder_id,
        title: r.title,
        content: '',
        entries: [],
        type: 'note' as RecordType,
        createdAt: r.created_at,
        updatedAt: r.updated_at,
      })))
      const loadingAfter = new Map(get().recordsLoading)
      loadingAfter.set(folderId, false)
      set({ records: newRecords, recordsLoading: loadingAfter })
    } catch {
      const loadingAfter = new Map(get().recordsLoading)
      loadingAfter.set(folderId, false)
      set({ recordsLoading: loadingAfter })
    }
  },
  saveRecord: async (recordId, content) => {
    const { records } = get()
    const newRecords = new Map(records)
    for (const [folderId, folderRecords] of newRecords) {
      const updated = folderRecords.map((r) =>
        r.id === recordId ? { ...r, content, updatedAt: new Date().toISOString() } : r
      )
      newRecords.set(folderId, updated)
    }
    set({ records: newRecords })

    try {
      await recordsApi.addRecordContent(recordId, 'text', content)
    } catch {
      // optimistic update already applied
    }
  },
}))
