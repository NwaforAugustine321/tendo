import { Link, NavLink } from 'react-router-dom'
import { panelTitle, type PrimarySection } from '../../lib/navigation'

type Props = {
  primary: PrimarySection
  onNavigate?: () => void
  fullWidth?: boolean
  onPanelEnter?: () => void
}

function navClass(isActive: boolean) {
  return [
    'block rounded-md px-2 py-1 text-[11px] transition-colors',
    isActive ? 'bg-zinc-800/50 text-zinc-200' : 'text-zinc-500 hover:bg-zinc-800/30 hover:text-zinc-300',
  ].join(' ')
}

function sectionLabel(text: string) {
  return <p className="px-0.5 text-[9px] font-medium uppercase tracking-wide text-zinc-600">{text}</p>
}

function ConversationsBody({ onNavigate }: { onNavigate?: () => void }) {
  const sessions = [
    { id: '1', title: 'Morning Sales Update' },
    { id: '2', title: 'Inventory Review' },
    { id: '3', title: 'Customer Debt Follow-up' },
  ]

  return (
    <div className="min-h-0 flex-1 space-y-3 overflow-y-auto px-2 py-2">
      <div>
        {sectionLabel('Quick actions')}
        <div className="mt-1 space-y-0.5">
          <Link to="/app/conversation/new" onClick={onNavigate} className={navClass(false)}>
            + New conversation
          </Link>
        </div>
      </div>
      <div>
        {sectionLabel('Recent sessions')}
        <ul className="mt-1 space-y-0.5">
          {sessions.map((s) => (
            <li key={s.id}>
              <NavLink
                to={`/app/conversation/${s.id}`}
                onClick={onNavigate}
                className={({ isActive }) => navClass(isActive)}
              >
                {s.title}
              </NavLink>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}

function BusinessBody({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <div className="min-h-0 flex-1 space-y-3 overflow-y-auto px-2 py-2">
      {sectionLabel('Business')}
      <div className="mt-1 space-y-0.5">
        <Link to="/app/business" onClick={onNavigate} className={navClass(false)}>Profile</Link>
        <Link to="/app/business" onClick={onNavigate} className={navClass(false)}>Understanding</Link>
        <Link to="/app/business" onClick={onNavigate} className={navClass(false)}>Settings</Link>
      </div>
    </div>
  )
}

function InventoryBody({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <div className="min-h-0 flex-1 space-y-3 overflow-y-auto px-2 py-2">
      {sectionLabel('Inventory')}
      <div className="mt-1 space-y-0.5">
        <Link to="/app/inventory" onClick={onNavigate} className={navClass(false)}>All products</Link>
        <Link to="/app/inventory" onClick={onNavigate} className={navClass(false)}>Low stock</Link>
        <Link to="/app/inventory" onClick={onNavigate} className={navClass(false)}>Movements</Link>
      </div>
    </div>
  )
}

function CustomersBody({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <div className="min-h-0 flex-1 space-y-3 overflow-y-auto px-2 py-2">
      {sectionLabel('Customers')}
      <div className="mt-1 space-y-0.5">
        <Link to="/app/customers" onClick={onNavigate} className={navClass(false)}>All customers</Link>
        <Link to="/app/customers" onClick={onNavigate} className={navClass(false)}>Outstanding debts</Link>
        <Link to="/app/customers" onClick={onNavigate} className={navClass(false)}>Suppliers</Link>
      </div>
    </div>
  )
}

function AnalyticsBody({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <div className="min-h-0 flex-1 space-y-3 overflow-y-auto px-2 py-2">
      {sectionLabel('Analytics')}
      <div className="mt-1 space-y-0.5">
        <Link to="/app/analytics" onClick={onNavigate} className={navClass(false)}>Overview</Link>
        <Link to="/app/analytics" onClick={onNavigate} className={navClass(false)}>Sales</Link>
        <Link to="/app/analytics" onClick={onNavigate} className={navClass(false)}>Payments</Link>
      </div>
    </div>
  )
}

export function SecondaryNav({ primary, onNavigate, fullWidth, onPanelEnter }: Props) {
  const title = panelTitle(primary)

  return (
    <aside
      className={`relative z-0 flex h-full min-h-0 flex-col border-zinc-800/60 bg-[#0f0f0f] ${fullWidth ? 'w-full border-r-0' : 'w-64 shrink-0 border-r'}`}
      aria-label="Explorer"
      onMouseEnter={onPanelEnter}
    >
      <div className="flex shrink-0 items-center border-b border-zinc-800/60 px-2 py-1.5">
        <h2 className="min-w-0 flex-1 truncate text-xs font-medium tracking-wide text-zinc-400">{title}</h2>
      </div>

      {primary === 'conversations' && <ConversationsBody onNavigate={onNavigate} />}
      {primary === 'business' && <BusinessBody onNavigate={onNavigate} />}
      {primary === 'inventory' && <InventoryBody onNavigate={onNavigate} />}
      {primary === 'customers' && <CustomersBody onNavigate={onNavigate} />}
      {primary === 'analytics' && <AnalyticsBody onNavigate={onNavigate} />}
    </aside>
  )
}
