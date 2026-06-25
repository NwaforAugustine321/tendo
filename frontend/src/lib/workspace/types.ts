/**
 * Core data types for the Radial Workspace feature.
 */

export type FolderColor = 'orange' | 'green' | 'blue' | 'teal' | 'cyan' | 'pink' | 'purple'

export type FolderIcon = 'folder' | 'briefcase' | 'wallet' | 'shopping-bag' | 'users' | 'file-text' | 'archive' | 'star' | 'heart' | 'zap' | 'globe' | 'code'

export type RecordType = 'note' | 'imported' | 'uploaded' | 'template'

/** Content entry types within a record */
export type EntryType = 'text' | 'image' | 'audio' | 'pdf' | 'camera' | 'voice'

export interface RecordEntry {
  id: string
  type: EntryType
  content: string // text content, or file URL/path for media
  createdAt: string
}

export interface Folder {
  id: string
  name: string
  color: FolderColor
  icon: FolderIcon
  recordCount: number
  createdAt: string
  updatedAt: string
}

export interface Record {
  id: string
  folderId: string
  title: string
  content: string
  entries: RecordEntry[]
  type: RecordType
  createdAt: string
  updatedAt: string
}

export type RadialAction =
  | { type: 'browse-folders' }
  | { type: 'new-folder' }
  | { type: 'new-record'; folderId?: string }
  | { type: 'import-data' }
  | { type: 'upload-file' }
  | { type: 'templates' }
  | { type: 'quick-note'; folderId?: string }

export type RadialViewState =
  | { view: 'actions' }
  | { view: 'folders'; folders: Folder[] }
  | { view: 'records'; folderId: string; records: Record[] }
  | { view: 'sources' }

export interface DragState {
  recordId: string
  sourceFolderId: string
  currentTargetFolderId: string | null
}

export interface ContextMenuState {
  target:
    | { type: 'folder'; folderId: string }
    | { type: 'record'; recordId: string; folderId: string }
  position: { x: number; y: number }
}
