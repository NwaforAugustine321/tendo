import { useCallback, useEffect, useRef, useState } from 'react'
import {
  X,
  FolderOpen,
  FolderPlus,
  FilePlus,
  Download,
  Upload,
  LayoutGrid,
  StickyNote,
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
} from 'lucide-react'
import clsx from 'clsx'
import { RadialMenuItem } from '../atoms'
import { useWorkspaceStore } from '../../store/workspace'
import { getHubPosition, isInVisibleArc } from '../../lib/workspace/radial-utils'
import { RADIAL_ANIMATION_MS, FOLDER_COLOR_CLASSES } from '../../lib/workspace/constants'
import type { Folder as FolderType, FolderIcon, Record as RecordType } from '../../lib/workspace/types'

const HUB_RADIUS = 140
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
  { label: 'New Record', icon: <FilePlus size={20} />, type: 'new-record' as const },
  { label: 'Upload File', icon: <Upload size={20} />, type: 'upload-file' as const },
  { label: 'Browse Folders', icon: <FolderOpen size={20} />, type: 'browse-folders' as const },
  { label: 'Quick Note', icon: <StickyNote size={20} />, type: 'quick-note' as const },
  { label: 'Templates', icon: <LayoutGrid size={20} />, type: 'templates' as const },
  { label: 'Import Data', icon: <Download size={20} />, type: 'import-data' as const },
]

export function RadialMenu() {
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
    const spacing = total > 1 ? 180 / (total - 1) : 0
    // Keep at least 2 items visible in the arc at all times
    // The visible arc is -90° to +90° (180° total)
    // We want the second-to-last item to stay at the edge when scrolling to the end
    const minItemsVisible = Math.min(2, total)
    const maxScroll = (total - minItemsVisible) * spacing
    return Math.max(-maxScroll, Math.min(maxScroll, offset))
  }, [getItemCount])

  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setRotationOffset((prev) => clampRotation(prev - e.deltaY * SCROLL_SENSITIVITY))
  }, [clampRotation])

  // Attach native wheel listener with passive: false to prevent browser back/forward navigation
  useEffect(() => {
    const el = containerRef.current
    if (!el || !radialMenuOpen) return

    const nativeWheelHandler = (e: WheelEvent) => {
      e.preventDefault()
      e.stopPropagation()
      setRotationOffset((prev) => clampRotation(prev - e.deltaY * SCROLL_SENSITIVITY))
    }

    el.addEventListener('wheel', nativeWheelHandler, { passive: false })
    return () => {
      el.removeEventListener('wheel', nativeWheelHandler)
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
          break
        case 'new-folder':
          createFolder('New Folder')
          closeRadialMenu()
          break
        case 'new-record':
          if (folders.length > 0) createRecord(folders[0].id, 'note')
          closeRadialMenu()
          break
        case 'quick-note':
          if (folders.length > 0) createRecord(folders[0].id, 'note', 'Quick Note')
          closeRadialMenu()
          break
        default:
          closeRadialMenu()
          break
      }
    },
    [folders, setRadialView, createFolder, createRecord, closeRadialMenu]
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

  if (!visible) return null

  const isOpen = radialMenuOpen && !animating
  const isClosing = !radialMenuOpen && animating
  const scaleClass = prefersReducedMotion.current
    ? ''
    : isOpen ? 'scale-100 opacity-100' : isClosing ? 'scale-95 opacity-0' : 'scale-95 opacity-0'

  const isFoldersView = radialMenuView.view === 'folders'
  const isRecordsView = radialMenuView.view === 'records'
  const isActionsView = radialMenuView.view === 'actions'

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
              className="absolute flex min-h-[44px] min-w-[44px] flex-col items-center justify-center gap-1.5 rounded-lg p-2 transition-all duration-200 hover:scale-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3ecf8e]/60"
              style={style}
            >
              <span className={colorClasses.text}>
                {getFolderIcon(folder.icon, 28)}
              </span>
              <span className="whitespace-nowrap text-[11px] font-medium text-zinc-300">{folder.name}</span>
              <span className="text-[10px] text-zinc-500">{folder.recordCount} Items</span>
            </button>
          )
        }
        if (item.kind === 'new-folder') {
          return (
            <button key="hub-new-folder" type="button" role="menuitem" onClick={() => createFolder('New Folder')}
              className="absolute flex min-h-[44px] min-w-[44px] flex-col items-center justify-center gap-1.5 rounded-lg p-2 transition-all duration-200 hover:scale-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3ecf8e]/60"
              style={style}
            >
              <span className="flex h-10 w-10 items-center justify-center rounded-full bg-[#3ecf8e] text-white"><Plus size={20} /></span>
              <span className="whitespace-nowrap text-[11px] font-medium text-zinc-300">New Folder</span>
            </button>
          )
        }
        if (item.kind === 'new-record') {
          return (
            <button key="hub-new-record" type="button" role="menuitem" onClick={() => { if (folders.length > 0) createRecord(folders[0].id, 'note'); closeRadialMenu() }}
              className="absolute flex min-h-[44px] min-w-[44px] flex-col items-center justify-center gap-1.5 rounded-lg p-2 transition-all duration-200 hover:scale-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3ecf8e]/60"
              style={style}
            >
              <span className="flex h-10 w-10 items-center justify-center rounded-full bg-[#3ecf8e] text-white"><Plus size={20} /></span>
              <span className="whitespace-nowrap text-[11px] font-medium text-zinc-300">New Record</span>
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
            className="absolute flex min-h-[44px] min-w-[44px] flex-col items-center justify-center gap-1 rounded-lg p-2 transition-all duration-200 hover:scale-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3ecf8e]/60"
            style={{ transform: `translate(${x}px, ${y}px) translate(-50%, -50%)`, opacity, pointerEvents: opacity < 0.3 ? 'none' : 'auto' }}
          >
            <span className="h-2 w-2 rounded-full bg-[#3ecf8e]" />
            <span className="max-w-[90px] truncate text-[11px] font-medium text-zinc-300">{record.title}</span>
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
      onWheel={(e) => { e.preventDefault(); e.stopPropagation() }}
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
          left: '325px',
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
            width: HUB_RADIUS + 80,
            height: (HUB_RADIUS + 80) * 2,
            top: -(HUB_RADIUS + 80),
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

        {/* Items positioned relative to center (0,0) */}
        <div className="absolute" style={{ left: 0, top: 0 }}>
          {renderItems()}
        </div>

        {/* Scroll hints */}
        <div className="absolute z-10 pointer-events-none text-zinc-600 text-xs" style={{ left: HUB_RADIUS / 2, top: -(HUB_RADIUS + 20) }} aria-hidden="true">▲</div>
        <div className="absolute z-10 pointer-events-none text-zinc-600 text-xs" style={{ left: HUB_RADIUS / 2, top: HUB_RADIUS + 10 }} aria-hidden="true">▼</div>
      </div>
    </div>
  )
}
