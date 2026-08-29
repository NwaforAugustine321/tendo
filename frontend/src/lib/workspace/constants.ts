/**
 * Constants for the Radial Workspace feature.
 */

import type { FolderColor, FolderIcon } from "./types";

export const FOLDER_COLOR_ROTATION: FolderColor[] = [
  "orange",
  "green",
  "blue",
  "teal",
  "cyan",
  "orange",
  "pink",
  "purple",
];

/** Map of FolderIcon values to their lucide-react component names */
export const FOLDER_ICON_MAP: Record<FolderIcon, string> = {
  folder: "Folder",
  briefcase: "Briefcase",
  wallet: "Wallet",
  "shopping-bag": "ShoppingBag",
  users: "Users",
  "file-text": "FileText",
  archive: "Archive",
  star: "Star",
  heart: "Heart",
  zap: "Zap",
  globe: "Globe",
  code: "Code",
};

/** List of available folder icons for the icon picker */
export const FOLDER_ICONS_LIST: FolderIcon[] = [
  "folder",
  "briefcase",
  "wallet",
  "shopping-bag",
  "users",
  "file-text",
  "archive",
  "star",
  "heart",
  "zap",
  "globe",
  "code",
];

/** Accepted file types for Import Data action */
export const IMPORT_FILE_TYPES = ".csv,.xlsx,.json";

/** Accepted file types for Upload File action */
export const UPLOAD_FILE_TYPES = ".pdf,.png,.jpg,.docx";

/** Max file size in bytes (25 MB) */
export const MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024;

/** Radial menu animation duration in ms */
export const RADIAL_ANIMATION_MS = 300;

/** Folder expand/collapse animation duration in ms */
export const FOLDER_ANIMATION_MS = 200;

/** Search debounce delay in ms */
export const SEARCH_DEBOUNCE_MS = 200;

/** Maximum folder name length */
export const MAX_FOLDER_NAME_LENGTH = 64;

/** Maximum record rename length */
export const MAX_RECORD_NAME_LENGTH = 100;

/** Drag initiation threshold in ms (hold duration) */
export const DRAG_HOLD_THRESHOLD_MS = 150;

/** Drag initiation threshold in px (movement distance) */
export const DRAG_MOVE_THRESHOLD_PX = 5;

/** Long-press threshold for context menu on touch (ms) */
export const LONG_PRESS_THRESHOLD_MS = 400;

/** Confirmation notification display duration (ms) */
export const NOTIFICATION_DURATION_MS = 3000;

/** Breadcrumb title max length before truncation */
export const BREADCRUMB_MAX_TITLE_LENGTH = 60;

/** Quick action button size in px */
export const QUICK_ACTION_BUTTON_SIZE = 56;

/** Quick action button margin from edges in px */
export const QUICK_ACTION_BUTTON_MARGIN = 16;

/** Minimum tap target size in px */
export const MIN_TAP_TARGET_SIZE = 44;

/** Responsive breakpoint (px) */
export const MOBILE_BREAKPOINT = 768;

/** Radial menu minimum margin from viewport edges on mobile */
export const RADIAL_MOBILE_MARGIN = 16;

/**
 * Prompt sent to Tendo when the user asks for an explanation but
 * there is no specific text to quote.
 *
 * Names the document as the subject so the request still makes
 * sense in a fresh session with no prior chat context.
 */
export const EXPLAIN_PROMPT =
  "Please explain what is happening and what it means for my operations.";

/**
 * Prompt for explaining a specific piece of text.
 *
 * The text is embedded in the message, so the request is
 * self-contained and carries no dependency on chat history.
 */
export function explainPrompt(text: string): string {
  const value = (text || "").trim();

  if (!value) return EXPLAIN_PROMPT;

  return (
    "Please explain the following and what it means for my operations:\n\n" +
    `"${value}"`
  );
}

/** Color mapping for Tailwind classes */
export const FOLDER_COLOR_CLASSES: Record<
  FolderColor,
  { bg: string; border: string; text: string }
> = {
  orange: {
    bg: "bg-orange-500",
    border: "border-orange-500",
    text: "text-orange-500",
  },
  green: {
    bg: "bg-green-500",
    border: "border-green-500",
    text: "text-green-500",
  },
  blue: { bg: "bg-blue-500", border: "border-blue-500", text: "text-blue-500" },
  teal: { bg: "bg-teal-500", border: "border-teal-500", text: "text-teal-500" },
  cyan: { bg: "bg-cyan-500", border: "border-cyan-500", text: "text-cyan-500" },
  pink: { bg: "bg-pink-500", border: "border-pink-500", text: "text-pink-500" },
  purple: {
    bg: "bg-purple-500",
    border: "border-purple-500",
    text: "text-purple-500",
  },
};
