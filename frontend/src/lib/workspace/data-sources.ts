import {
  MessageCircle,
  Mail,
  CalendarDays,
  FileText,
  Video,
  HardDrive,
  Hash,
  Image,
  ShoppingCart,
  CreditCard,
  Landmark,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

export interface DataSource {
  id: string
  label: string
  icon: LucideIcon
}

export const DATA_SOURCES: DataSource[] = [
  { id: 'whatsapp', label: 'WhatsApp', icon: MessageCircle },
  { id: 'gmail', label: 'Gmail', icon: Mail },
  { id: 'calendar', label: 'Calendar', icon: CalendarDays },
  { id: 'paper-invoices', label: 'Paper invoices', icon: FileText },
  { id: 'meeting-recordings', label: 'Meeting recordings', icon: Video },
  { id: 'google-drive', label: 'Google Drive', icon: HardDrive },
  { id: 'slack', label: 'Slack', icon: Hash },
  { id: 'photos', label: 'Photos', icon: Image },
  { id: 'shopify', label: 'Shopify', icon: ShoppingCart },
  { id: 'pos', label: 'POS', icon: CreditCard },
  { id: 'bank-transactions', label: 'Bank transactions', icon: Landmark },
]
