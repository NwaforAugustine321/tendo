export type InboxTab = 'primary' | 'insights' | 'attention' | 'recommendations'

export type InboxMessage = {
  id: string
  sender: string
  senderEmail: string
  recipient: string
  subject: string
  preview: string
  body: string
  date: string
  fullDate: string
  read: boolean
  starred: boolean
  tab: InboxTab
  avatarColor: string
}

export const TABS: { id: InboxTab; label: string; badge?: number; badgeColor?: string }[] = [
  { id: 'primary', label: 'Primary' },
  { id: 'insights', label: 'Insights' },
  { id: 'attention', label: 'Needs Attention', badge: 1, badgeColor: 'bg-red-500/20 text-red-400' },
  { id: 'recommendations', label: 'Recommendations', badge: 1, badgeColor: 'bg-amber-500/20 text-amber-400' },
]
