/**
 * Character configuration — change these to switch characters.
 */

// Character type: 'adult_female' | 'adult_male' | 'alien'
export const CHARACTER_TYPE = 'alien'

// Character name: 'cristine' | 'fiona' | 'grace' | 'maya' (female) | 'jay' | 'luke' | 'preston' | 'wes' (male) | 'alien'
export const CHARACTER_NAME = 'maya'

// Model file name (usually same as character name)
export const CHARACTER_MODEL = `${CHARACTER_NAME}.gltf`

// Derived paths
export const CHARACTER_PATH = `/assets/characters/${CHARACTER_TYPE}/${CHARACTER_NAME}/`
export const ANIMATION_PATH = `/assets/animations/${CHARACTER_TYPE}/`

// Character display size (bottom-right overlay)
export const CHARACTER_WIDTH = 380
export const CHARACTER_HEIGHT = 420

// Camera settings
export const CAMERA_ALPHA = Math.PI / 2
export const CAMERA_BETA = 1.3
export const CAMERA_RADIUS = 2.2
export const CAMERA_TARGET_Y = 1.5
