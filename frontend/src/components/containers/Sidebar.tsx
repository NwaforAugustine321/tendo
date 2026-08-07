import { useState, useRef, useEffect, useCallback } from 'react'
import { NavLink } from 'react-router-dom'
import {
  Inbox,
  Lightbulb,
  History,
  Archive,
  Plus,
  Menu,
  ChevronDown,
  Folder,
  MessageCircle,
  Loader2,
} from 'lucide-react'
import clsx from 'clsx'
import { toast } from 'sonner'
import { useAuth } from '../../context/auth'
import { useWorkspaceStore } from '../../store/workspace'
import { useBusinessStore } from '../../store/business'
import { listDataSources, disconnectDataSource, onboardWhatsApp } from '../../lib/services/integrations'
import * as recordsApi from '../../lib/services/records'

type NavItem = {
  to?: string
  label: string
  icon: React.ReactNode
  end?: boolean
  disabled?: boolean
}

const PRIMARY_NAV: NavItem[] = [
  { to: '/app', label: 'Activities', icon: <Inbox size={18} />, end: true },
  { to: '/app/insights', label: 'Quick Insight', icon: <Lightbulb size={18} /> },
  { label: 'Recent', icon: <History size={18} />, disabled: true },
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

const CODE = "AQIZMgohzOX1Fg8BH7E26-3iuwLKboSSEpaR6vUoIIZXpL60lsyoLFE4yVXB5mlbHO6QbtTA445X5C3U0pTScMYEBikNeugXjSdT8JiqAJxkt6JqETYfssDVGyxiBZWZ3CMhixaNwNSRQ7afdL98eSGuTAg-8G50mD7IP_WdUEUENCjkeb_DRC3ti32hAWXNnS8cK0QT1lMk1J2WbiBCaBBfXHirG3-cWfeNTOQzvX3G5La1NG3ODwpKcmp95LsV99cJalQZnKOYAI65NkiwjNLRmPCnXHGRO_rFJl6NGaeWit_NqNrY1Lwus-t_BKhQKbdCXAhMaAsWb7LftkxZq8mvymeb9rNbo3tJ4HXcazO4tsHkMObO_DC2JWIWWlfis45SOtV8FHqkbivxeyzfGOpHCJ7AGJEzWr00JD0gBS2iNQ"

export function Sidebar({ className, collapsed, onToggle }: SidebarProps) {
  const { user } = useAuth()
  const { currentProfile } = useBusinessStore()
  const { folders, createFolder, fetchFolders } = useWorkspaceStore()
  const [moreExpanded, setMoreExpanded] = useState(false)
  const [creatingFolder, setCreatingFolder] = useState(false)
  const [newFolderName, setNewFolderName] = useState('')
  const [whatsappConnected, setWhatsappConnected] = useState(false)
  const [addingRecord, setAddingRecord] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    fetchFolders()
  }, [])

  useEffect(() => {
    if (creatingFolder) inputRef.current?.focus()
  }, [creatingFolder])

  const fetchWhatsAppStatus = useCallback(async () => {
    if (!currentProfile?.id) return
    try {
      const sources = await listDataSources(currentProfile.id)
      const wa = sources.find((s) => s.source_type === 'whatsapp' && s.status === 'active')
      setWhatsappConnected(!!wa)
    } catch {
      setWhatsappConnected(false)
    }
  }, [currentProfile?.id])

  useEffect(() => {
    fetchWhatsAppStatus()
  }, [fetchWhatsAppStatus])

  const handleCreateFolder = () => {
    const name = newFolderName.trim()
    if (name) {
      createFolder(name)
    }
    setNewFolderName('')
    setCreatingFolder(false)
  }

  const handleConnectWhatsApp = async () => {

    if (!currentProfile?.id) return
    if (whatsappConnected) {
      try {
        await disconnectDataSource(currentProfile.id, 'whatsapp')
        setWhatsappConnected(false)
      } catch {
        toast.error('Failed disconnecting WhatsApp Source. Please try again.')
      }
    } else {
      try {
        const WHATSAPP_CONFIG_ID = import.meta.env.VITE_WHATSAPP_CONFIG_ID
        if (!WHATSAPP_CONFIG_ID) return

        const FB = (window as any).FB
    
        if (!FB) return

        onboardWhatsApp(currentProfile!.id, CODE).then(() => setWhatsappConnected(true))

        // FB.login(
        //   (response: any) => {
        //     if (response.authResponse && response.status === 'connected') {
        //       console.log(response.authResponse)
        //       // const code = response.authResponse.code
        //       onboardWhatsApp(currentProfile!.id, CODE).then(() => setWhatsappConnected(true))
        //     }else{
        //       toast.error('Failed to connect WhatsApp Source. Please try again.')
        //     }
        //   },
        //   {
        //     config_id: WHATSAPP_CONFIG_ID,
        //     response_type: 'code',
        //     override_default_response_type: true,
        //     redirect_uri: import.meta.env.VITE_WHATSAPP_REDIRECT_URI, 
        //     extras: {
        //       setup: {},
        //       featureType: 'whatsapp_business_app_onboarding'
        //     },
        //   }
        // )
      } catch {
        toast.error('Failed to connect WhatsApp Source. Please try again.')
      }
    }
  }

  const handleAdd = async () => {
    if (addingRecord) return
    setAddingRecord(true)
    try {
      const hashId = crypto.randomUUID().replace(/-/g, '').slice(0, 6)
      const title = `#${hashId}`
      const folderId = folders.length > 0 ? folders[0].id : ''
      const apiRecord = await recordsApi.createRecord(folderId, title)
      // Add record to workspace store so popup can find it
      const store = useWorkspaceStore.getState()
      const records = new Map(store.records)
      const folderRecords = records.get(folderId) || []
      records.set(folderId, [...folderRecords, {
        id: apiRecord.id,
        folderId,
        title: apiRecord.title || title,
        content: '',
        entries: [],
        type: 'note' as const,
        createdAt: apiRecord.created_at || new Date().toISOString(),
        updatedAt: apiRecord.updated_at || new Date().toISOString(),
      }])
      useWorkspaceStore.setState({ records })
      // Open the record in the floating popup modal
      store.openRecord(apiRecord.id)
      // Mark the new record as read (user just created it)
      recordsApi.markRecordRead(apiRecord.id).catch(() => {})
      // Notify Inbox to refresh its record list
      window.dispatchEvent(new CustomEvent('tendo:open-new-record'))
    } catch {
      toast.error('Failed to create record')
    } finally {
      setAddingRecord(false)
    }
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
        <div className="flex-1" />
        <button
          type="button"
          onClick={handleAdd}
          disabled={addingRecord}
          className={clsx(
            'flex items-center justify-center rounded-lg shadow-sm',
            'bg-zinc-800 border border-zinc-700/80',
            'text-[12px] font-medium text-zinc-200',
            'transition-all hover:shadow-md hover:border-zinc-600 hover:bg-zinc-750',
            'active:scale-[0.97]',
            'h-7 w-7',
            addingRecord && 'opacity-60 cursor-not-allowed'
          )}
          title="Add record"
        >
          {addingRecord ? <Loader2 size={14} className="animate-spin text-zinc-300" /> : <Plus size={14} className="text-zinc-300" />}
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

      {/* Connect WhatsApp — collapsed state */}
      {collapsed && (
        <div className="flex justify-center px-1.5">
          <button
            type="button"
            onClick={handleConnectWhatsApp}
            title={whatsappConnected ? 'WhatsApp (Enabled)' : 'Connect WhatsApp'}
            className={clsx(
              'flex h-8 w-8 items-center justify-center rounded-full transition-colors hover:bg-white/5',
              whatsappConnected ? 'text-[#3ecf8e]' : 'text-zinc-500'
            )}
          >
            <MessageCircle size={18} />
          </button>
        </div>
      )}

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

          {/* Connect WhatsApp */}
          <button
            type="button"
            onClick={handleConnectWhatsApp}
            className="flex w-full items-center gap-2.5 rounded-r-full py-1 pl-4 pr-3 text-[12px] text-zinc-400 transition-colors hover:bg-white/5 hover:text-zinc-200"
          >
            <MessageCircle size={14} className={clsx('shrink-0', whatsappConnected ? 'text-[#3ecf8e]' : 'text-zinc-500')} />
            <span className="flex-1 truncate text-left">{whatsappConnected ? 'WhatsApp' : 'Connect WhatsApp'}</span>
            {whatsappConnected && (
              <span className="rounded bg-[#3ecf8e]/15 px-1.5 py-0.5 text-[10px] font-medium text-[#3ecf8e]">Enabled</span>
            )}
          </button>
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
