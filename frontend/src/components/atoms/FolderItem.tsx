import { useRef, useEffect, type ReactNode } from 'react'
import { ChevronRight, Folder, Briefcase, Wallet, ShoppingBag, Users, FileText, Archive, Star, Heart, Zap, Globe, Code } from 'lucide-react'
import clsx from 'clsx'
import type { Folder as FolderType, FolderIcon } from '../../lib/workspace/types'

function getFolderIcon(iconName: FolderIcon, size: number = 16) {
  const icons: Record<FolderIcon, typeof Folder> = {
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
  const Icon = icons[iconName] || Folder
  return <Icon size={size} />
}

type Props = {
  folder: FolderType
  isExpanded: boolean
  onToggle: () => void
  onContextMenu: (e: React.MouseEvent) => void
  renaming?: { name: string; onChange: (name: string) => void; onSave: () => void; onCancel: () => void }
  children?: ReactNode
}

export function FolderItem({ folder, isExpanded, onToggle, onContextMenu, renaming, children }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (renaming) {
      setTimeout(() => {
        inputRef.current?.focus()
        inputRef.current?.select()
      }, 0)
    }
  }, [!!renaming])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      onToggle()
    }
  }

  return (
    <div>
      <button
        type="button"
        onClick={renaming ? undefined : onToggle}
        onContextMenu={onContextMenu}
        onKeyDown={renaming ? undefined : handleKeyDown}
        aria-expanded={isExpanded}
        className={clsx(
          'flex w-full items-center gap-3 rounded-lg px-2.5 py-1.5 text-left',
          'transition-colors duration-150',
          isExpanded
            ? 'bg-zinc-800/60 border border-zinc-700/40'
            : 'hover:bg-white/5 border border-transparent',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3ecf8e]/60'
        )}
      >
        <span className="shrink-0 text-zinc-400">
          {getFolderIcon(folder.icon, 16)}
        </span>
        <div className="flex flex-1 flex-col min-w-0">
          {renaming ? (
            <input
              ref={inputRef}
              type="text"
              value={renaming.name}
              onChange={(e) => renaming.onChange(e.target.value)}
              onBlur={renaming.onSave}
              onKeyDown={(e) => {
                e.stopPropagation()
                if (e.key === 'Enter') renaming.onSave()
                if (e.key === 'Escape') renaming.onCancel()
              }}
              className="w-full rounded border border-[#3ecf8e]/40 bg-[#0a0a0a] px-2 py-0.5 text-sm text-zinc-200 outline-none"
              onClick={(e) => e.stopPropagation()}
            />
          ) : (
            <>
              <span className="truncate text-sm font-medium text-zinc-200">{folder.name}</span>
              <span className="text-[11px] text-zinc-500">{folder.recordCount} Items</span>
            </>
          )}
        </div>
        <ChevronRight
          size={14}
          className={clsx(
            'shrink-0 text-zinc-500 transition-transform duration-200',
            isExpanded && 'rotate-90'
          )}
        />
      </button>

      <div
        className={clsx(
          'overflow-hidden transition-[max-height] duration-200 ease-in-out',
          isExpanded ? 'max-h-[2000px]' : 'max-h-0'
        )}
      >
        <div className="pl-4 pt-1">{children}</div>
      </div>
    </div>
  )
}
