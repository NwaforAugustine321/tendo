export type PrimarySection = 'insights' | 'recent' | 'analytics'

export function primaryFromPathname(pathname: string): PrimarySection {
  if (pathname.startsWith('/app/insights')) return 'insights'
  if (pathname.startsWith('/app/recent')) return 'recent'
  if (pathname.startsWith('/app/analytics')) return 'analytics'
  return 'insights'
}

export function panelTitle(primary: PrimarySection): string {
  switch (primary) {
    case 'insights': return 'Insights'
    case 'recent': return 'Recent'
    case 'analytics': return 'Analytics'
  }
}
