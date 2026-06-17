import type { ReactNode } from 'react'
import { NavLink } from 'react-router-dom'
import type { PrimarySection } from '../../lib/navigation'

type Props = {
  orientation?: 'vertical' | 'horizontal'
  onNavigate?: () => void
  activePrimary: PrimarySection
  onPrimaryClick?: () => void
}

function railItemClass(active: boolean, orientation: 'vertical' | 'horizontal') {
  const edge = orientation === 'vertical' ? 'border-l-2' : 'border-b-2'
  if (orientation === 'vertical') {
    return [
      'relative z-0 flex h-11 w-full items-center justify-center gap-0 overflow-hidden rounded-r-md',
      'transition-[background-color,color,box-shadow,gap,padding] duration-200 ease-out',
      'group-hover/rail:justify-start group-hover/rail:gap-2 group-hover/rail:bg-[#141414] group-hover/rail:px-2.5 group-hover/rail:shadow-lg',
      edge,
      active ? 'border-[#3ecf8e] bg-white/[0.06] text-white' : 'border-transparent text-zinc-500 hover:text-zinc-300',
    ].join(' ')
  }
  return [
    'relative z-0 flex h-10 w-11 shrink-0 items-center justify-center gap-0 overflow-hidden rounded-md',
    'transition-[min-width,background-color,color,box-shadow,gap,padding] duration-200 ease-out',
    'group-hover/rail:min-w-[8.25rem] group-hover/rail:justify-start group-hover/rail:bg-[#141414] group-hover/rail:px-2 group-hover/rail:shadow-md',
    edge,
    active ? 'border-[#3ecf8e] bg-white/[0.06] text-white' : 'border-transparent text-zinc-500 hover:text-zinc-300',
  ].join(' ')
}

const railItemLabelClass =
  'pointer-events-none max-w-0 truncate whitespace-nowrap text-left text-xs font-medium text-zinc-400 opacity-0 transition-[max-width,opacity] duration-200 ease-out group-hover/rail:max-w-[7.5rem] group-hover/rail:opacity-100'

const NAV_ITEMS: { id: PrimarySection; to: string; label: string; icon: ReactNode }[] = [
  {
    id: 'conversations',
    to: '/app',
    label: 'Conversations',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v10Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
      </svg>
    ),
  },
  {
    id: 'business',
    to: '/app/business',
    label: 'Business',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
        <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V9Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
        <path d="M9 22V12h6v10" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
      </svg>
    ),
  },
  {
    id: 'inventory',
    to: '/app/inventory',
    label: 'Inventory',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
        <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
        <path d="M3.27 6.96L12 12.01l8.73-5.05M12 22.08V12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
  },
  {
    id: 'customers',
    to: '/app/customers',
    label: 'Customers',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        <circle cx="9" cy="7" r="4" stroke="currentColor" strokeWidth="1.5" />
        <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
  },
  {
    id: 'analytics',
    to: '/app/analytics',
    label: 'Analytics',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
        <path d="M18 20V10M12 20V4M6 20v-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
  },
]

export function IconRail({ orientation = 'vertical', onNavigate, activePrimary, onPrimaryClick }: Props) {
  const fireClick = () => {
    onPrimaryClick?.()
    onNavigate?.()
  }

  const core = (
    <>
      {NAV_ITEMS.map((item) => (
        <div key={item.id} className={orientation === 'vertical' ? 'h-11 w-full shrink-0' : 'h-10 shrink-0'}>
          <NavLink
            to={item.to}
            end={item.to === '/app'}
            className={() => railItemClass(activePrimary === item.id, orientation)}
            aria-label={item.label}
            onClick={fireClick}
          >
            <span className="flex shrink-0 items-center justify-center [&>svg]:shrink-0">{item.icon}</span>
            <span className={railItemLabelClass}>{item.label}</span>
          </NavLink>
        </div>
      ))}
    </>
  )

  if (orientation === 'horizontal') {
    return (
      <div
        className="group/rail flex w-full flex-row items-center gap-1 overflow-x-auto overflow-y-visible border-b border-zinc-800/90 bg-[#0f0f0f] px-2 py-1"
        onClick={onNavigate}
      >
        {core}
      </div>
    )
  }

  return (
    <aside
      className="group/rail pointer-events-auto absolute inset-y-0 left-0 z-30 flex w-[52px] flex-col overflow-visible border-r border-zinc-800/90 bg-[#0f0f0f] shadow-none transition-[width,box-shadow] duration-200 ease-out hover:w-44 hover:shadow-2xl"
      aria-label="Primary navigation"
    >
      <div className="flex w-full flex-col overflow-visible py-2">{core}</div>
      <div className="min-h-0 flex-1" aria-hidden="true" />
      <div className="mt-auto flex w-full flex-col overflow-visible border-t border-zinc-800/90 py-2">
        <div className="h-11 w-full shrink-0">
          <NavLink
            to="/app/settings"
            className={() => railItemClass(false, orientation)}
            aria-label="Settings"
            onClick={fireClick}
          >
            <span className="flex shrink-0 items-center justify-center [&>svg]:shrink-0">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                <path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z" stroke="currentColor" strokeWidth="1.5" />
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68 1.65 1.65 0 0 0 10 3.17V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9c.26.38.6.65 1.01.77H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </span>
            <span className={railItemLabelClass}>Settings</span>
          </NavLink>
        </div>
      </div>
    </aside>
  )
}
