import { useState, useRef, useEffect } from 'react'
import { NavLink } from 'react-router-dom'
import {
  Inbox,
  Lightbulb,
  History,
  Archive,
  Star,
  Plus,
  Menu,
  ChevronDown,
  Folder,
} from 'lucide-react'
import clsx from 'clsx'
import { useAuth } from '../../context/auth'
import { useWorkspaceStore } from '../../store/workspace'

type NavItem = {
  to?: string
  label: string
  icon: React.ReactNode
  end?: boolean
  disabled?: boolean
}

const PRIMARY_NAV: NavItem[] = [
  { to: '/app', label: 'Activities', icon: <Inbox size={18} />, end: true },
  { label: 'Insights', icon: <Lightbulb size={18} />, disabled: true },
  { label: 'Recent', icon: <History size={18} />, disabled: true },
  { label: 'Favorites', icon: <Star size={18} />, disabled: true },
  { label: 'Archive', icon: <Archive size={18} />, disabled: true },
]

function NavItemLink({ item, collapsed }: { item: NavItem; collapsed: boolean }) {
  if (item.disabled || !item.to) {
    return (
      <button
        type="button"
        title={collapsed ? item.label : undefined}
        className={clsx(
          'group flex items-center transition-colors cursor-default',
          collapsed
            ? 'justify-center rounded-full mx-auto h-8 w-8'
            : 'gap-3 rounded-r-full py-1 pl-4 pr-3 text-[13px] font-medium',
          'text-zinc-500'
        )}
        disabled
      >
        <span className="shrink-0">{item.icon}</span>
        {!collapsed && <span className="truncate">{item.label}</span>}
      </button>
    )
  }

  return (
    <NavLink
      to={item.to}
      end={item.end}
      title={collapsed ? item.label : undefined}
      className={({ isActive }) =>
        clsx(
          'group flex items-center transition-colors',
          collapsed
            ? 'justify-center rounded-full mx-auto h-8 w-8'
            : 'gap-3 rounded-r-full py-1 pl-4 pr-3 text-[13px] font-medium',
          isActive
            ? 'bg-emerald-500/15 text-emerald-400'
            : 'text-zinc-400 hover:bg-white/5 hover:text-zinc-200'
        )
      }
    >
      <span className="shrink-0">{item.icon}</span>
      {!collapsed && <span className="truncate">{item.label}</span>}
    </NavLink>
  )
}

type SidebarProps = {
  className?: string
  collapsed: boolean
  onToggle: () => void
}

export function Sidebar({ className, collapsed, onToggle }: SidebarProps) {
  const { user } = useAuth()
  const { folders, createFolder, createRecord, fetchFolders } = useWorkspaceStore()
  const [moreExpanded, setMoreExpanded] = useState(false)
  const [creatingFolder, setCreatingFolder] = useState(false)
  const [newFolderName, setNewFolderName] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    fetchFolders()
  }, [])

  useEffect(() => {
    if (creatingFolder) inputRef.current?.focus()
  }, [creatingFolder])

  const handleCreateFolder = () => {
    const name = newFolderName.trim()
    if (name) {
      createFolder(name)
    }
    setNewFolderName('')
    setCreatingFolder(false)
  }

  const handleAdd = () => {
    // Create a record with a hash ID title and open it in the floating record panel
    const hashId = crypto.randomUUID().replace(/-/g, '').slice(0, 6)
    const title = `#${hashId}`
    const folderId = folders.length > 0 ? folders[0].id : ''
    createRecord(folderId, 'note', title)

    // Wait briefly for the record to be created, then open it
    setTimeout(() => {
      const { records, openRecord } = useWorkspaceStore.getState()
      // Find the most recently created record
      for (const [, folderRecords] of records) {
        if (folderRecords.length > 0) {
          const latest = folderRecords[folderRecords.length - 1]
          openRecord(latest.id)
          return
        }
      }
    }, 600)
  }

  return (
    <aside
      className={clsx(
        'flex h-full flex-col border-r border-zinc-800/60 bg-[#0f0f0f] transition-[width] duration-200 ease-out',
        collapsed ? 'w-[68px]' : 'w-[220px]',
        className
      )}
      aria-label="Main navigation"
    >
      {/* Top row: hamburger + New Chat button */}
      <div className={clsx('flex items-center gap-2 px-3 py-3', collapsed && 'flex-col gap-3')}>
        <button
          type="button"
          onClick={onToggle}
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-zinc-400 transition-colors hover:bg-white/5 hover:text-zinc-200"
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          <Menu size={20} />
        </button>
        <button
          type="button"
          onClick={handleAdd}
          className={clsx(
            'flex items-center gap-2 rounded-2xl shadow-sm',
            'bg-zinc-800 border border-zinc-700/80',
            'text-[13px] font-medium text-zinc-200',
            'transition-all hover:shadow-md hover:border-zinc-600 hover:bg-zinc-750',
            'active:scale-[0.97]',
            collapsed ? 'h-10 w-10 justify-center px-0' : 'px-5 py-2.5'
          )}
          title={collapsed ? 'Add' : undefined}
        >
          <Plus size={18} className="text-zinc-300" />
          {!collapsed && <span>Add</span>}
        </button>
      </div>

      {/* Primary navigation */}
      <nav className={clsx('flex flex-col gap-0 py-0.5', collapsed ? 'px-1.5' : 'px-0')}>
        {PRIMARY_NAV.map((item) => (
          <NavItemLink key={item.label} item={item} collapsed={collapsed} />
        ))}
      </nav>

      {/* More section — collapsible, shows folders */}
      {!collapsed && (
        <div className="mt-1">
          <button
            type="button"
            onClick={() => setMoreExpanded(!moreExpanded)}
            className="flex w-full items-center gap-3 py-1 pl-4 pr-3 text-[13px] font-medium text-zinc-500 transition-colors hover:text-zinc-300"
          >
            <ChevronDown size={16} className={clsx('transition-transform', !moreExpanded && '-rotate-90')} />
            <span>More</span>
          </button>

          {moreExpanded && (
            <div className="flex flex-col gap-0 pl-4">
              {folders.map((folder) => (
                <button
                  key={folder.id}
                  type="button"
                  className="flex items-center gap-2.5 rounded-r-full py-1 pl-4 pr-3 text-[12px] text-zinc-400 transition-colors hover:bg-white/5 hover:text-zinc-200"
                >
                  <Folder size={14} className="shrink-0 text-zinc-500" />
                  <span className="truncate">{folder.name}</span>
                </button>
              ))}
              {folders.length === 0 && (
                <p className="pl-4 py-2 text-[11px] text-zinc-600">No folders yet</p>
              )}
            </div>
          )}
        </div>
      )}

      {/* Divider */}
      <div className={clsx('my-2 border-t border-zinc-800/60', collapsed ? 'mx-2' : 'mx-4')} />

      {/* Labels section — click + to create folder */}
      {!collapsed && (
        <div>
          <div className="flex items-center justify-between px-4 py-1.5">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">Labels</span>
            <button
              type="button"
              onClick={() => setCreatingFolder(true)}
              className="flex h-5 w-5 items-center justify-center rounded text-zinc-500 hover:bg-white/5 hover:text-zinc-300"
              aria-label="Create folder"
            >
              <Plus size={14} />
            </button>
          </div>

          {/* Inline folder creation input */}
          {creatingFolder && (
            <div className="px-4 py-1">
              <input
                ref={inputRef}
                type="text"
                value={newFolderName}
                onChange={(e) => setNewFolderName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleCreateFolder()
                  if (e.key === 'Escape') { setCreatingFolder(false); setNewFolderName('') }
                }}
                onBlur={handleCreateFolder}
                placeholder="Folder name..."
                className="w-full rounded border border-zinc-700 bg-[#0a0a0a] px-2 py-1 text-[12px] text-zinc-200 placeholder-zinc-600 focus:border-emerald-600 focus:outline-none"
              />
            </div>
          )}
        </div>
      )}

      {/* Spacer */}
      <div className="flex-1" />

      {/* User section */}
      <div className="border-t border-zinc-800/60 px-3 py-3">
        <div className={clsx('flex items-center', collapsed ? 'justify-center' : 'gap-2.5 px-1')}>
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-zinc-700 bg-zinc-800">
            <span className="text-[11px] font-bold text-zinc-400">
              {(user?.name || 'U')[0].toUpperCase()}
            </span>
          </div>
          {!collapsed && (
            <div className="min-w-0 flex-1">
              <p className="truncate text-[12px] font-medium text-zinc-300">{user?.name || 'User'}</p>
              <p className="truncate text-[10px] text-zinc-500">{user?.email || ''}</p>
            </div>
          )}
        </div>
      </div>

    </aside>
  )
}
