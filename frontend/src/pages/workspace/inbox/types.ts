import type { SnapPriority } from "../../../lib/services/snaps";

export type InboxTab =
  | "primary"
  | "insights"
  | "attention"
  | "recommendations"
  | "priority";

export type InboxMessage = {
  id: string;
  sender: string;
  senderEmail: string;
  recipient: string;
  subject: string;
  preview: string;
  body: string;
  date: string;
  fullDate: string;
  read: boolean;
  starred: boolean;
  tab: InboxTab;
  avatarColor: string;
  snapId?: string;
  snapPriority?: SnapPriority;
  snapConfidence?: number;
  snapDomain?: string;
};

export const TABS: {
  id: InboxTab;
  label: string;
  badgeColor?: string;
}[] = [
  { id: "primary", label: "Inbox & Files" },
  { id: "insights", label: "Quick Insight" },
  {
    id: "attention",
    label: "Needs Attention",
    badgeColor: "bg-red-500/20 text-red-400",
  },
  {
    id: "recommendations",
    label: "Recommendations",
    badgeColor: "bg-amber-500/20 text-amber-400",
  },
  {
    id: "priority",
    label: "Priority",
    badgeColor: "bg-emerald-500/20 text-emerald-400",
  },
];
