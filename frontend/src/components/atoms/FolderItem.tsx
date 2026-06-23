import type { ReactNode } from 'react'
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
  children?: ReactNode
}

export function FolderItem({ folder, isExpanded, onToggle, onContextMenu, children }: Props) {
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
        onClick={onToggle}
        onContextMenu={onContextMenu}
        onKeyDown={handleKeyDown}
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
        {/* Folder icon in zinc color */}
        <span className="shrink-0 text-zinc-400">
          {getFolderIcon(folder.icon, 16)}
        </span>
        {/* Folder name and count */}
        <div className="flex flex-1 flex-col min-w-0">
          <span className="truncate text-sm font-medium text-zinc-200">{folder.name}</span>
          <span className="text-[11px] text-zinc-500">{folder.recordCount} Items</span>
        </div>
        {/* Chevron */}
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
