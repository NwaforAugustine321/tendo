/**
 * Folder name utilities — normalization, unique name generation, color assignment.
 */

import type { Folder, FolderColor } from './types'
import { FOLDER_COLOR_ROTATION, MAX_FOLDER_NAME_LENGTH } from './constants'

/**
 * Normalize a folder name: trim whitespace, enforce max length,
 * default to "Untitled Folder" if empty.
 */
export function normalizeFolderName(name: string): string {
  const trimmed = name.trim()
  if (!trimmed) return 'Untitled Folder'
  return trimmed.slice(0, MAX_FOLDER_NAME_LENGTH)
}

/**
 * Generate a unique folder name by appending (1), (2), etc. if the name
 * already exists in the list.
 */
export function generateUniqueName(baseName: string, existingNames: string[]): string {
  const normalized = normalizeFolderName(baseName)
  if (!existingNames.includes(normalized)) return normalized

  let suffix = 1
  while (existingNames.includes(`${normalized} (${suffix})`)) {
    suffix++
  }
  return `${normalized} (${suffix})`
}

/**
 * Get the next folder color based on how many folders already exist.
 * Cycles through the color rotation array.
 */
export function getNextFolderColor(existingFolders: Folder[]): FolderColor {
  return FOLDER_COLOR_ROTATION[existingFolders.length % FOLDER_COLOR_ROTATION.length]
}
