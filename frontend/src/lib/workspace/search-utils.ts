/**
 * Search/filter utilities for the workspace.
 */

/**
 * Filter items by query using case-insensitive substring matching.
 *
 * @param items - Array of items to filter
 * @param query - Search query string
 * @param nameAccessor - Function to extract the name/searchable text from an item
 * @returns Filtered array of items whose name contains the query
 */
export function filterByQuery<T>(
  items: T[],
  query: string,
  nameAccessor: (item: T) => string
): T[] {
  if (!query.trim()) return items

  const lowerQuery = query.toLowerCase()
  return items.filter((item) => nameAccessor(item).toLowerCase().includes(lowerQuery))
}
