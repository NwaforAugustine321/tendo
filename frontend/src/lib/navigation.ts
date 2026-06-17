export type PrimarySection = 'conversations' | 'business' | 'inventory' | 'customers' | 'analytics'

export function primaryFromPathname(pathname: string): PrimarySection {
  if (pathname.startsWith('/app/business')) return 'business'
  if (pathname.startsWith('/app/inventory')) return 'inventory'
  if (pathname.startsWith('/app/customers')) return 'customers'
  if (pathname.startsWith('/app/analytics')) return 'analytics'
  return 'conversations'
}

export function panelTitle(primary: PrimarySection): string {
  switch (primary) {
    case 'conversations': return 'Sessions'
    case 'business': return 'Business'
    case 'inventory': return 'Inventory'
    case 'customers': return 'Customers'
    case 'analytics': return 'Analytics'
  }
}
