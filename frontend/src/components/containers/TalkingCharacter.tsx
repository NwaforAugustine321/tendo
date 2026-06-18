import { useEffect, useRef } from 'react'
import * as BABYLON from '@babylonjs/core'
import '@babylonjs/loaders'
import {
  CHARACTER_PATH,
  CHARACTER_MODEL,
  ANIMATION_PATH,
  CHARACTER_WIDTH,
  CHARACTER_HEIGHT,
  CAMERA_ALPHA,
  CAMERA_BETA,
  CAMERA_RADIUS,
  CAMERA_TARGET_Y,
} from '../../lib/character-config'

type Props = {
  isSpeaking?: boolean
  flipX?: boolean
  rightOffset?: number
}

export function TalkingCharacter({ isSpeaking = false, flipX = false, rightOffset = 0 }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const engineRef = useRef<BABYLON.Engine | null>(null)
  const animGroupsRef = useRef<{ [key: string]: BABYLON.AnimationGroup }>({})

  useEffect(() => {
    const groups = animGroupsRef.current
    if (isSpeaking) {
      groups['lipsync']?.play(true)
      groups['gesture']?.play(true)
    } else {
      groups['lipsync']?.stop()
      groups['gesture']?.stop()
    }
  }, [isSpeaking])

  useEffect(() => {
    if (!canvasRef.current) return

    const engine = new BABYLON.Engine(canvasRef.current, true, {
      preserveDrawingBuffer: true,
      stencil: true,
    })
    engineRef.current = engine

    const scene = new BABYLON.Scene(engine)
    scene.clearColor = new BABYLON.Color4(0, 0, 0, 0)

    const camera = new BABYLON.ArcRotateCamera(
      'cam',
      CAMERA_ALPHA,
      CAMERA_BETA,
      CAMERA_RADIUS,
      new BABYLON.Vector3(0, CAMERA_TARGET_Y, 0),
      scene
    )
    camera.attachControl(canvasRef.current, false)
    camera.lowerRadiusLimit = 1.5
    camera.upperRadiusLimit = 4
    camera.wheelPrecision = 50
    camera.panningSensibility = 0

    const hemiLight = new BABYLON.HemisphericLight('hemi', new BABYLON.Vector3(0, 1, 0), scene)
    hemiLight.intensity = 0.7

    const dirLight = new BABYLON.DirectionalLight('dir', new BABYLON.Vector3(-0.5, -1, 1), scene)
    dirLight.intensity = 0.5

    BABYLON.SceneLoader.ImportMesh(
      '',
      CHARACTER_PATH,
      CHARACTER_MODEL,
      scene,
      (_meshes, _ps, _sk, animationGroups) => {
        animationGroups.forEach((ag) => ag.stop())
        loadAnimation(scene, 'stand_idle', ANIMATION_PATH + 'stand_idle.glb', true)
        loadAnimation(scene, 'blink', ANIMATION_PATH + 'blink.glb', true)
        loadAnimation(scene, 'face_idle', ANIMATION_PATH + 'face_idle.glb', true)
        loadAnimation(scene, 'lipsync', ANIMATION_PATH + 'lipsync.glb', false)
        loadAnimation(scene, 'gesture', ANIMATION_PATH + 'gesture.glb', false)
      },
      undefined,
      (_scene, message) => console.warn('Character load error:', message)
    )

    engine.runRenderLoop(() => scene.render())

    const handleResize = () => engine.resize()
    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      engine.dispose()
      engineRef.current = null
      animGroupsRef.current = {}
    }
  }, [])

  function loadAnimation(scene: BABYLON.Scene, name: string, url: string, autoPlay: boolean) {
    BABYLON.SceneLoader.ImportAnimations(
      url, '', scene, false,
      BABYLON.SceneLoaderAnimationGroupLoadingMode.NoSync,
      undefined,
      (scene) => {
        const lastGroup = scene.animationGroups[scene.animationGroups.length - 1]
        if (lastGroup) {
          animGroupsRef.current[name] = lastGroup
          if (autoPlay) lastGroup.play(true)
          else lastGroup.stop()
        }
      }
    )
  }

  return (
    <div
      className="pointer-events-none fixed z-50"
      style={{
        width: CHARACTER_WIDTH,
        height: CHARACTER_HEIGHT,
        bottom: '5px',
        right: `${rightOffset}px`,
        transform: flipX ? 'scaleX(-1)' : undefined,
      }}
    >
      <canvas ref={canvasRef} className="h-full w-full" style={{ background: 'transparent' }} />
    </div>
  )
}
