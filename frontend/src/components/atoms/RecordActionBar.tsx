import { useEffect } from 'react'
import { FolderInput, FolderTree, Pencil, Trash2 } from 'lucide-react'
import clsx from 'clsx'

type Action = 'move' | 'organise' | 'rename' | 'delete'

type Props = {
  position: { x: number; y: number }
  onAction: (action: Action) => void
  onClose: () => void
}

const items: { action: Action; label: string; icon: React.ReactNode; danger?: boolean }[] = [
  { action: 'move', label: 'Move', icon: <FolderInput size={14} /> },
  { action: 'organise', label: 'Organise', icon: <FolderTree size={14} /> },
  { action: 'rename', label: 'Rename', icon: <Pencil size={14} /> },
  { action: 'delete', label: 'Delete', icon: <Trash2 size={14} />, danger: true },
]

export function RecordActionBar({ position, onAction, onClose }: Props) {
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement
      if (!target.closest('[data-record-action-bar]')) {
        onClose()
      }
    }
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }

    document.addEventListener('mousedown', handleClick)
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('mousedown', handleClick)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [onClose])

  return (
    <div
      data-record-action-bar
      role="menu"
      className={clsx(
        'absolute z-50 min-w-[140px] rounded-lg border border-white/10',
        'bg-[#1a1a1a] py-1 shadow-xl'
      )}
      style={{ left: position.x, top: position.y }}
    >
      {items.map((item) => (
        <button
          key={item.action}
          type="button"
          role="menuitem"
          onClick={() => onAction(item.action)}
          className={clsx(
            'flex w-full items-center gap-2 px-3 py-1.5 text-left text-sm transition-colors',
            'hover:bg-white/5',
            item.danger ? 'text-red-400 hover:text-red-300' : 'text-zinc-300 hover:text-white'
          )}
        >
          {item.icon}
          {item.label}
        </button>
      ))}
    </div>
  )
}
