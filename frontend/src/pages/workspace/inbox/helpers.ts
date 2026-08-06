export function areaToSender(area: string): string {
  const map: Record<string, string> = {
    sales: 'Sales Insights',
    finance: 'Finance Alert',
    operations: 'Operations',
    customers: 'Customer Insights',
    inventory: 'Inventory Alert',
    general: 'Tendo AI',
    hr: 'Team Updates',
    marketing: 'Marketing',
  }
  return map[area] || 'Tendo AI'
}

export function areaToColor(area: string): string {
  const map: Record<string, string> = {
    sales: 'bg-green-600',
    finance: 'bg-amber-600',
    operations: 'bg-blue-600',
    customers: 'bg-purple-600',
    inventory: 'bg-cyan-600',
    general: 'bg-emerald-600',
    hr: 'bg-pink-600',
    marketing: 'bg-orange-600',
  }
  return map[area] || 'bg-zinc-600'
}

export function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  if (diffMins < 60) return `${diffMins}m ago`
  const diffHours = Math.floor(diffMins / 60)
  if (diffHours < 24) return `${diffHours}h ago`
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

export function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMin = Math.floor(diffMs / 60000)
  const diffHr = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMin < 1) return 'Just now'
  if (diffMin < 60) return `${diffMin} min ago`
  if (diffHr < 24) return `${diffHr} hr ago`
  if (diffDays === 1) return 'Yesterday'
  if (diffDays < 7) return `${diffDays} days ago`
  if (date.getFullYear() === now.getFullYear()) {
    return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
  }
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}
