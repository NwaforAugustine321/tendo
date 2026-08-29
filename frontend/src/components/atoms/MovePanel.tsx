import { useEffect } from 'react'
import { X, Folder } from 'lucide-react'
import clsx from 'clsx'
import type { Folder as FolderType } from '../../lib/workspace/types'

type Props = {
  folders: FolderType[]
  excludeFolderId: string
  onMoveToFolder: (targetFolderId: string) => void
  onClose: () => void
}

export function MovePanel({ folders, excludeFolderId, onMoveToFolder, onClose }: Props) {
  const availableFolders = folders.filter((f) => f.id !== excludeFolderId)

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  return (
    <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/50" onClick={onClose}>
      <div
        className="w-full max-w-xl rounded-xl border border-white/10 bg-[#1a1a1a] p-5 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <span className="text-base font-medium text-zinc-200">Move to folder</span>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="rounded p-1.5 text-zinc-500 hover:bg-white/5 hover:text-zinc-300"
          >
            <X size={16} />
          </button>
        </div>

        {availableFolders.length === 0 ? (
          <p className="py-6 text-center text-sm text-zinc-500">No other folders available</p>
        ) : (
          <ul className="max-h-[400px] space-y-1.5 overflow-y-auto">
            {availableFolders.map((folder) => (
              <li
                key={folder.id}
                className={clsx(
                  'flex items-center gap-3 rounded-lg px-3 py-2.5',
                  'border border-transparent',
                  'hover:border-dashed hover:border-zinc-600'
                )}
              >
                <span className="shrink-0 text-zinc-400">
                  <Folder size={18} />
                </span>
                <span className="flex-1 truncate text-sm text-zinc-300">{folder.name}</span>
                <span className="text-[11px] text-zinc-600">{folder.recordCount} items</span>
                <button
                  type="button"
                  onClick={() => onMoveToFolder(folder.id)}
                  className={clsx(
                    'shrink-0 rounded-md px-3 py-1 text-xs font-medium',
                    'border border-[#3ecf8e]/40 text-[#3ecf8e]',
                    'transition-colors hover:border-[#3ecf8e] hover:bg-[#3ecf8e]/10'
                  )}
                >
                  Move
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
