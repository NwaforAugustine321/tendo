/**
 * Character configuration — change the ACTIVE_CHARACTER to switch.
 *
 * Available characters:
 *   adult_female: cristine, fiona, grace, maya
 *   adult_male: jay, luke, preston, wes
 *   alien: alien
 */

// ─── CHANGE THIS TO SWITCH CHARACTER ─────────────────────
export const ACTIVE_CHARACTER: CharacterOption = 'luke'
// ──────────────────────────────────────────────────────────

type CharacterOption =
  | 'cristine' | 'fiona' | 'grace' | 'maya'
  | 'jay' | 'luke' | 'preston' | 'wes'
  | 'alien'

const CHARACTER_MAP: Record<CharacterOption, { type: string; path: string; model: string; animPath: string }> = {
  cristine: { type: 'adult_female', path: '/assets/characters/adult_female/cristine/', model: 'cristine.gltf', animPath: '/assets/animations/adult_female/' },
  fiona: { type: 'adult_female', path: '/assets/characters/adult_female/fiona/', model: 'fiona.gltf', animPath: '/assets/animations/adult_female/' },
  grace: { type: 'adult_female', path: '/assets/characters/adult_female/grace/', model: 'grace.gltf', animPath: '/assets/animations/adult_female/' },
  maya: { type: 'adult_female', path: '/assets/characters/adult_female/maya/', model: 'maya.gltf', animPath: '/assets/animations/adult_female/' },
  jay: { type: 'adult_male', path: '/assets/characters/adult_male/jay/', model: 'jay.gltf', animPath: '/assets/animations/adult_male/' },
  luke: { type: 'adult_male', path: '/assets/characters/adult_male/luke/', model: 'luke.gltf', animPath: '/assets/animations/adult_male/' },
  preston: { type: 'adult_male', path: '/assets/characters/adult_male/preston/', model: 'preston.gltf', animPath: '/assets/animations/adult_male/' },
  wes: { type: 'adult_male', path: '/assets/characters/adult_male/wes/', model: 'wes.gltf', animPath: '/assets/animations/adult_male/' },
  alien: { type: 'alien', path: '/assets/characters/alien/', model: 'alien.gltf', animPath: '/assets/animations/alien/' },
}

const config = CHARACTER_MAP[ACTIVE_CHARACTER]

export const CHARACTER_PATH = config.path
export const CHARACTER_MODEL = config.model
export const ANIMATION_PATH = config.animPath

// Display size
export const CHARACTER_WIDTH = 380
export const CHARACTER_HEIGHT = 420

// Camera settings
export const CAMERA_ALPHA = Math.PI / 2
export const CAMERA_BETA = 1.3
export const CAMERA_RADIUS = 2.2
export const CAMERA_TARGET_Y = 1.5
