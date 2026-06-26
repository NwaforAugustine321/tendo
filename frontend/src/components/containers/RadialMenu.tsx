import { useCallback, useEffect, useRef, useState } from 'react'
import {
  X,
  FolderOpen,
  FolderPlus,
  Plus,
  Folder,
  Briefcase,
  Wallet,
  ShoppingBag,
  Users,
  FileText,
  Archive,
  Star,
  Heart,
  Zap,
  Globe,
  Code,
  Cable,
  Settings,
  Lightbulb,
} from 'lucide-react'
import clsx from 'clsx'
import { RadialMenuItem } from '../atoms'
import { useWorkspaceStore } from '../../store/workspace'
import { getHubPosition, isInVisibleArc } from '../../lib/workspace/radial-utils'
import { RADIAL_ANIMATION_MS, FOLDER_COLOR_CLASSES } from '../../lib/workspace/constants'
import { DATA_SOURCES, type DataSource } from '../../lib/workspace/data-sources'
import { showToast } from '../../lib/workspace/toast'
import type { Folder as FolderType, FolderIcon, Record as RecordType } from '../../lib/workspace/types'

const HUB_RADIUS = 130
const SCROLL_SENSITIVITY = 0.4
const TOUCH_SENSITIVITY = 0.6

function getFolderIcon(iconName: FolderIcon, size: number = 28) {
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

const radialActions = [
  { label: 'New Folder', icon: <FolderPlus size={20} />, type: 'new-folder' as const },
  { label: 'Browse Folders', icon: <FolderOpen size={20} />, type: 'browse-folders' as const },
  { label: 'Connect Sources', icon: <Cable size={20} />, type: 'connect-sources' as const },
  { label: 'Insights', icon: <Lightbulb size={20} />, type: 'insights' as const },
  { label: 'Settings', icon: <Settings size={20} />, type: 'settings' as const },
]

export function RadialMenu({ sidebarOpen = true }: { sidebarOpen?: boolean }) {
  const {
    radialMenuOpen,
    radialMenuView,
    folders,
    records,
    closeRadialMenu,
    setRadialView,
    createFolder,
    createRecord,
  } = useWorkspaceStore()

  const [animating, setAnimating] = useState(false)
  const [visible, setVisible] = useState(false)
  const [rotationOffset, setRotationOffset] = useState(0)
  const containerRef = useRef<HTMLDivElement>(null)
  const touchStartY = useRef<number | null>(null)
  const prefersReducedMotion = useRef(false)

  useEffect(() => {
    prefersReducedMotion.current = window.matchMedia(
      '(prefers-reduced-motion: reduce)'
    ).matches
  }, [])

  useEffect(() => {
    setRotationOffset(0)
  }, [radialMenuView])

  useEffect(() => {
    if (radialMenuOpen) {
      setVisible(true)
      setRotationOffset(0)
      if (!prefersReducedMotion.current) {
        setAnimating(true)
        const timer = setTimeout(() => setAnimating(false), RADIAL_ANIMATION_MS)
        return () => clearTimeout(timer)
      }
    } else {
      if (!prefersReducedMotion.current) {
        setAnimating(true)
        const timer = setTimeout(() => {
          setVisible(false)
          setAnimating(false)
        }, RADIAL_ANIMATION_MS)
        return () => clearTimeout(timer)
      } else {
        setVisible(false)
      }
    }
  }, [radialMenuOpen])

  const getItemCount = useCallback(() => {
    if (radialMenuView.view === 'sources') return DATA_SOURCES.length
    if (radialMenuView.view === 'folders') {
      const viewFolders = radialMenuView.folders || []
      return viewFolders.length + 2
    }
    if (radialMenuView.view === 'records') {
      return radialMenuView.records?.length || 0
    }
    return radialActions.length
  }, [radialMenuView])

  const clampRotation = useCallback((offset: number): number => {
    const total = getItemCount()
    if (total <= 1) return 0
    // Match the spacing logic in getHubPosition
    const MIN_SPACING = 35
    const arcSize = 180
    const naturalSpacing = total > 1 ? arcSize / (total - 1) : 0
    const spacing = Math.max(MIN_SPACING, naturalSpacing)
    // Allow full rotation — items can scroll until last reaches top position
    // and first reaches bottom position
    const maxScroll = spacing * (total - 1)
    return Math.max(-maxScroll, Math.min(maxScroll, offset))
  }, [getItemCount])

  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setRotationOffset((prev) => clampRotation(prev - e.deltaY * SCROLL_SENSITIVITY))
  }, [clampRotation])

  // Attach wheel listener to the document when menu is open so scrolling works anywhere over the overlay
  useEffect(() => {
    if (!radialMenuOpen) return

    const nativeWheelHandler = (e: WheelEvent) => {
      e.preventDefault()
      setRotationOffset((prev) => clampRotation(prev - e.deltaY * SCROLL_SENSITIVITY))
    }

    document.addEventListener('wheel', nativeWheelHandler, { passive: false })
    return () => {
      document.removeEventListener('wheel', nativeWheelHandler)
    }
  }, [radialMenuOpen, clampRotation])

  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    e.stopPropagation()
    touchStartY.current = e.touches[0].clientY
  }, [])

  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    if (touchStartY.current === null) return
    e.preventDefault()
    e.stopPropagation()
    const deltaY = e.touches[0].clientY - touchStartY.current
    touchStartY.current = e.touches[0].clientY
    setRotationOffset((prev) => clampRotation(prev + deltaY * TOUCH_SENSITIVITY))
  }, [clampRotation])

  const handleTouchEnd = useCallback((e: React.TouchEvent) => {
    e.stopPropagation()
    touchStartY.current = null
  }, [])

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (!radialMenuOpen) return
      if (e.key === 'Escape') { closeRadialMenu(); return }
      if (e.key === 'Tab') {
        e.preventDefault()
        const items = containerRef.current?.querySelectorAll<HTMLButtonElement>(
          'button[role="menuitem"], button[aria-label]'
        )
        if (!items || items.length === 0) return
        const arr = Array.from(items)
        const idx = arr.indexOf(document.activeElement as HTMLButtonElement)
        const next = e.shiftKey ? (idx - 1 + arr.length) % arr.length : (idx + 1) % arr.length
        arr[next]?.focus()
      }
      if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') {
        e.preventDefault()
        setRotationOffset((prev) => clampRotation(prev + 15))
      }
      if (e.key === 'ArrowDown' || e.key === 'ArrowRight') {
        e.preventDefault()
        setRotationOffset((prev) => clampRotation(prev - 15))
      }
    },
    [radialMenuOpen, closeRadialMenu, clampRotation]
  )

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])

  const handleBackdropClick = useCallback(
    (e: React.MouseEvent) => {
      if (e.target === e.currentTarget) closeRadialMenu()
    },
    [closeRadialMenu]
  )

  const handleActionClick = useCallback(
    (actionType: string) => {
      switch (actionType) {
        case 'browse-folders':
          setRadialView({ view: 'folders', folders })
          window.dispatchEvent(new Event('tendo:open-sidebar'))
          break
        case 'connect-sources':
          setRadialView({ view: 'sources' })
          break
        case 'new-folder':
          createFolder('New Folder')
          closeRadialMenu()
          window.dispatchEvent(new Event('tendo:open-sidebar'))
          break
        case 'insights':
          closeRadialMenu()
          window.location.href = '/app/insights'
          break
        case 'settings':
          closeRadialMenu()
          window.location.href = '/app/settings'
          break
        default:
          closeRadialMenu()
          break
      }
    },
    [folders, setRadialView, createFolder, closeRadialMenu]
  )

  const handleFolderClick = useCallback(
    (folder: FolderType) => {
      const folderRecords = records.get(folder.id) || []
      setRadialView({ view: 'records', folderId: folder.id, records: folderRecords })
    },
    [records, setRadialView]
  )

  const handleRecordClick = useCallback(
    (record: RecordType) => {
      useWorkspaceStore.getState().setActiveRecord(record.id)
      useWorkspaceStore.getState().setActiveFolderId(record.folderId)
      closeRadialMenu()
    },
    [closeRadialMenu]
  )

  const handleBackToActions = useCallback(() => {
    setRadialView({ view: 'actions' })
  }, [setRadialView])

  const handleSourceClick = useCallback(
    (source: DataSource) => {
      showToast(`${source.label} selected — connection coming soon`)
      closeRadialMenu()
    },
    [closeRadialMenu]
  )

  if (!visible) return null

  const isOpen = radialMenuOpen && !animating
  const isClosing = !radialMenuOpen && animating
  const scaleClass = prefersReducedMotion.current
    ? ''
    : isOpen ? 'scale-100 opacity-100' : isClosing ? 'scale-95 opacity-0' : 'scale-95 opacity-0'

  const isFoldersView = radialMenuView.view === 'folders'
  const isRecordsView = radialMenuView.view === 'records'
  const isActionsView = radialMenuView.view === 'actions'
  const isSourcesView = radialMenuView.view === 'sources'

  const renderItems = () => {
    if (isActionsView) {
      return radialActions.map((action, index) => {
        const { angleDeg } = getHubPosition(index, radialActions.length, HUB_RADIUS, rotationOffset)
        const { visible: arcVisible, opacity } = isInVisibleArc(angleDeg)
        return (
          <RadialMenuItem
            key={action.type}
            icon={action.icon}
            label={action.label}
            angle={angleDeg}
            radius={HUB_RADIUS}
            onClick={() => handleActionClick(action.type)}
            index={index}
            total={radialActions.length}
            arcOpacity={opacity}
            arcVisible={arcVisible}
          />
        )
      })
    }

    if (isSourcesView) {
      return DATA_SOURCES.map((source, index) => {
        const { angleDeg } = getHubPosition(index, DATA_SOURCES.length, HUB_RADIUS, rotationOffset)
        const { visible: arcVisible, opacity } = isInVisibleArc(angleDeg)
        const Icon = source.icon
        return (
          <RadialMenuItem
            key={source.id}
            icon={<Icon size={20} />}
            label={source.label}
            angle={angleDeg}
            radius={HUB_RADIUS}
            onClick={() => handleSourceClick(source)}
            index={index}
            total={DATA_SOURCES.length}
            arcOpacity={opacity}
            arcVisible={arcVisible}
          />
        )
      })
    }

    if (isFoldersView) {
      const viewFolders = radialMenuView.view === 'folders' ? radialMenuView.folders : folders
      const allItems = [
        ...viewFolders.map((f) => ({ kind: 'folder' as const, folder: f })),
        { kind: 'new-folder' as const, folder: null },
        { kind: 'new-record' as const, folder: null },
      ]
      const total = allItems.length

      return allItems.map((item, index) => {
        const { angleDeg } = getHubPosition(index, total, HUB_RADIUS, rotationOffset)
        const { visible: arcVisible, opacity } = isInVisibleArc(angleDeg)
        if (!arcVisible) return null

        const angleRad = (angleDeg * Math.PI) / 180
        const x = HUB_RADIUS * Math.cos(angleRad)
        const y = HUB_RADIUS * Math.sin(angleRad)
        const style = {
          transform: `translate(${x}px, ${y}px) translate(-50%, -50%)`,
          opacity,
          pointerEvents: (opacity < 0.3 ? 'none' : 'auto') as React.CSSProperties['pointerEvents'],
        }

        if (item.kind === 'folder' && item.folder) {
          const folder = item.folder
          const colorClasses = FOLDER_COLOR_CLASSES[folder.color]
          return (
            <button key={folder.id} type="button" role="menuitem" onClick={() => handleFolderClick(folder)}
              className="group absolute flex min-h-[44px] min-w-[44px] items-center gap-3 rounded-lg p-2 transition-all duration-200 hover:scale-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3ecf8e]/60"
              style={style}
            >
              <span className="whitespace-nowrap text-[11px] font-medium text-zinc-400 group-hover:text-white transition-colors">
                {folder.name}
              </span>
              <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#1a1a1a] border border-white/10 shadow-md group-hover:border-[#3ecf8e]/40 transition-colors ${colorClasses.text}`}>
                {getFolderIcon(folder.icon, 18)}
              </span>
            </button>
          )
        }
        if (item.kind === 'new-folder') {
          return (
            <button key="hub-new-folder" type="button" role="menuitem" onClick={() => createFolder('New Folder')}
              className="group absolute flex min-h-[44px] min-w-[44px] items-center gap-3 rounded-lg p-2 transition-all duration-200 hover:scale-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3ecf8e]/60"
              style={style}
            >
              <span className="whitespace-nowrap text-[11px] font-medium text-zinc-400 group-hover:text-white transition-colors">
                New Folder
              </span>
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#3ecf8e] text-white"><Plus size={18} /></span>
            </button>
          )
        }
        if (item.kind === 'new-record') {
          return (
            <button key="hub-new-record" type="button" role="menuitem" onClick={() => { if (folders.length > 0) createRecord(folders[0].id, 'note'); closeRadialMenu() }}
              className="group absolute flex min-h-[44px] min-w-[44px] items-center gap-3 rounded-lg p-2 transition-all duration-200 hover:scale-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3ecf8e]/60"
              style={style}
            >
              <span className="whitespace-nowrap text-[11px] font-medium text-zinc-400 group-hover:text-white transition-colors">
                New Record
              </span>
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#3ecf8e] text-white"><Plus size={18} /></span>
            </button>
          )
        }
        return null
      })
    }

    if (isRecordsView && radialMenuView.view === 'records') {
      const viewRecords = radialMenuView.records
      return viewRecords.map((record, index) => {
        const { angleDeg } = getHubPosition(index, viewRecords.length, HUB_RADIUS, rotationOffset)
        const { visible: arcVisible, opacity } = isInVisibleArc(angleDeg)
        if (!arcVisible) return null
        const angleRad = (angleDeg * Math.PI) / 180
        const x = HUB_RADIUS * Math.cos(angleRad)
        const y = HUB_RADIUS * Math.sin(angleRad)
        return (
          <button key={record.id} type="button" role="menuitem" onClick={() => handleRecordClick(record)}
            className="group absolute flex min-h-[44px] min-w-[44px] items-center gap-3 rounded-lg p-2 transition-all duration-200 hover:scale-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3ecf8e]/60"
            style={{ transform: `translate(${x}px, ${y}px) translate(-50%, -50%)`, opacity, pointerEvents: opacity < 0.3 ? 'none' : 'auto' }}
          >
            <span className="max-w-[70px] truncate whitespace-nowrap text-[11px] font-medium text-zinc-400 group-hover:text-white transition-colors">
              {record.title}
            </span>
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#1a1a1a] border border-white/10 shadow-md group-hover:border-[#3ecf8e]/40 transition-colors">
              <span className="h-2 w-2 rounded-full bg-[#3ecf8e]" />
            </span>
          </button>
        )
      })
    }

    return null
  }

  return (
    <div
      className="fixed inset-0 z-[100]"
      onClick={handleBackdropClick}
      aria-hidden={!radialMenuOpen}
    >
      <div
        ref={containerRef}
        role="menu"
        aria-label="Hub action menu"
        className={clsx(
          'absolute',
          !prefersReducedMotion.current && 'transition-all duration-300 ease-out',
          scaleClass
        )}
        style={{
          left: sidebarOpen ? '325px' : '65px',
          bottom: '25%',
          marginBottom: '0px',
        }}
        onWheel={handleWheel}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
      >
        {/* Semicircle background */}
        <div
          className="absolute rounded-r-full bg-[#111111]/95 border border-white/10 border-l-0 shadow-2xl pointer-events-none"
          style={{
            width: HUB_RADIUS + 70,
            height: (HUB_RADIUS + 70) * 2,
            top: -(HUB_RADIUS + 70),
            left: -10,
          }}
          aria-hidden="true"
        />

        {/* Curved dashed track/rail */}
        <svg
          className="absolute pointer-events-none"
          style={{
            width: HUB_RADIUS * 2 + 20,
            height: HUB_RADIUS * 2 + 20,
            top: -(HUB_RADIUS + 10),
            left: -(HUB_RADIUS + 10),
          }}
          aria-hidden="true"
        >
          <path
            d={`M ${HUB_RADIUS + 10} 0 A ${HUB_RADIUS} ${HUB_RADIUS} 0 0 1 ${HUB_RADIUS + 10} ${HUB_RADIUS * 2 + 20}`}
            fill="none"
            stroke="rgba(255,255,255,0.1)"
            strokeWidth="1.5"
            strokeDasharray="6 4"
          />
        </svg>

        {/* X Close / Back button at the center anchor */}
        <button
          type="button"
          onClick={isActionsView ? closeRadialMenu : handleBackToActions}
          aria-label={isActionsView ? 'Close hub menu' : 'Back to actions'}
          className={clsx(
            'absolute z-20 flex h-12 w-12 items-center justify-center',
            'rounded-full bg-[#1a1a1a] border border-white/10 text-zinc-400',
            'transition-colors hover:border-white/20 hover:text-white',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3ecf8e]/60',
            'min-h-[44px] min-w-[44px]'
          )}
          style={{ left: -24, top: -24 }}
        >
          <X size={20} />
        </button>

        {/* Items positioned relative to center (0,0) — clip left side */}
        <div className="absolute z-[105] overflow-hidden pointer-events-none" style={{ left: -10, top: -(HUB_RADIUS + 70), width: HUB_RADIUS + 80, height: (HUB_RADIUS + 70) * 2 }}>
          <div className="absolute pointer-events-auto" style={{ left: 10, top: HUB_RADIUS + 70 }}>
            {renderItems()}
          </div>
        </div>

        {/* Scroll hints */}
        <div className="absolute z-10 pointer-events-none text-zinc-600 text-xs" style={{ left: HUB_RADIUS / 2, top: -(HUB_RADIUS + 20) }} aria-hidden="true">▲</div>
        <div className="absolute z-10 pointer-events-none text-zinc-600 text-xs" style={{ left: HUB_RADIUS / 2, top: HUB_RADIUS + 10 }} aria-hidden="true">▼</div>
      </div>
    </div>
  )
}
