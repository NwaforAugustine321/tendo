/**
 * Radial position math utilities.
 * Converts item indices to x,y positions along a circle circumference.
 */

/**
 * Get the x,y position for an item in a radial layout.
 * Items are distributed evenly around a circle, starting from the top (12 o'clock).
 *
 * @param index - The item's index (0-based)
 * @param total - Total number of items
 * @param radius - Distance from center in pixels
 * @returns { x, y } offset from center
 */
export function getRadialPosition(
  index: number,
  total: number,
  radius: number
): { x: number; y: number } {
  if (total <= 0) return { x: 0, y: 0 }

  // Start from top (270° in standard math coords = -90° = top)
  const angleStep = (2 * Math.PI) / total
  const angle = angleStep * index - Math.PI / 2 // offset to start at top

  const x = radius * Math.cos(angle)
  const y = radius * Math.sin(angle)

  return { x, y }
}

/**
 * Get the position for an item along a RIGHT-FACING semicircle hub.
 * The semicircle arc spans from -90° (top) to +90° (bottom), extending to the right.
 *
 * @param index - The item's index (0-based)
 * @param total - Total number of items to distribute
 * @param radius - Distance from center in pixels
 * @param rotationOffset - Rotation offset in degrees (from scrolling)
 * @returns { x, y, angleDeg } position and the computed angle in degrees
 */
export function getHubPosition(
  index: number,
  total: number,
  radius: number,
  rotationOffset: number = 0
): { x: number; y: number; angleDeg: number } {
  if (total <= 0) return { x: 0, y: 0, angleDeg: 0 }

  // Distribute items evenly across 180° arc
  // If there's only 1 item, place it at 0° (directly to the right)
  const spacing = total > 1 ? 180 / (total - 1) : 0
  // Item's base angle: start at -90° (top), increment by spacing
  const baseAngle = -90 + spacing * index

  // Apply rotation offset
  const angleDeg = baseAngle + rotationOffset

  // Convert to radians for position calculation
  const angleRad = (angleDeg * Math.PI) / 180

  // x extends to the right (cos), y extends down (sin)
  const x = radius * Math.cos(angleRad)
  const y = radius * Math.sin(angleRad)

  return { x, y, angleDeg }
}

/**
 * Check if an angle (in degrees) is within the visible semicircle arc.
 * The visible arc is from -90° to +90° (right-facing half).
 *
 * @param angleDeg - The angle in degrees to check
 * @param buffer - Optional buffer in degrees for fade-out zone (default 10)
 * @returns Object with visibility state and opacity value
 */
export function isInVisibleArc(
  angleDeg: number,
  buffer: number = 10
): { visible: boolean; opacity: number } {
  const minAngle = -90
  const maxAngle = 90

  // Fully visible
  if (angleDeg >= minAngle && angleDeg <= maxAngle) {
    // Fade near edges
    if (angleDeg < minAngle + buffer) {
      const t = (angleDeg - minAngle) / buffer
      return { visible: true, opacity: t }
    }
    if (angleDeg > maxAngle - buffer) {
      const t = (maxAngle - angleDeg) / buffer
      return { visible: true, opacity: t }
    }
    return { visible: true, opacity: 1 }
  }

  // Outside visible range
  return { visible: false, opacity: 0 }
}
