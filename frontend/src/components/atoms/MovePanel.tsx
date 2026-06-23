import { useEffect } from 'react'
import { X } from 'lucide-react'
import clsx from 'clsx'
import type { Folder } from '../../lib/workspace/types'
import { FOLDER_COLOR_CLASSES } from '../../lib/workspace/constants'

type Props = {
  folders: Folder[]
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
    <div
      className={clsx(
        'w-full max-w-xs rounded-lg border border-white/10',
        'bg-[#1a1a1a] p-3 shadow-xl'
      )}
    >
      <div className="mb-3 flex items-center justify-between">
        <span className="text-sm font-medium text-zinc-200">Move to folder</span>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close move panel"
          className={clsx(
            'rounded p-1 text-zinc-500 transition-colors',
            'hover:bg-white/5 hover:text-zinc-300',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3ecf8e]/60'
          )}
        >
          <X size={14} />
        </button>
      </div>

      {availableFolders.length === 0 ? (
        <p className="py-2 text-center text-xs text-zinc-500">No other folders available</p>
      ) : (
        <ul className="space-y-1">
          {availableFolders.map((folder) => {
            const colorClasses = FOLDER_COLOR_CLASSES[folder.color]
            return (
              <li
                key={folder.id}
                className={clsx(
                  'flex items-center gap-2 rounded-md px-2 py-1.5',
                  'hover:bg-white/5'
                )}
              >
                <span className={clsx('h-2.5 w-2.5 shrink-0 rounded-sm', colorClasses.bg)} />
                <span className="flex-1 truncate text-sm text-zinc-300">{folder.name}</span>
                <button
                  type="button"
                  onClick={() => onMoveToFolder(folder.id)}
                  className={clsx(
                    'shrink-0 rounded px-2 py-0.5 text-[11px] font-medium',
                    'border border-[#3ecf8e]/40 text-[#3ecf8e]',
                    'transition-colors hover:border-[#3ecf8e] hover:bg-[#3ecf8e]/10',
                    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3ecf8e]/60'
                  )}
                >
                  Move here
                </button>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
