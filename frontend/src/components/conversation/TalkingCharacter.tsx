import { useEffect, useRef, useCallback } from 'react'
import * as BABYLON from '@babylonjs/core'
import '@babylonjs/loaders'

type Props = {
  /** Text for the character to speak aloud */
  speakText?: string
  /** Whether the character should play talking animation */
  isSpeaking?: boolean
}

const CHARACTER_PATH = '/assets/characters/adult_female/cristine/'
const ANIMATION_PATH = '/assets/animations/adult_female/'

export function TalkingCharacter({ speakText, isSpeaking = false }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const engineRef = useRef<BABYLON.Engine | null>(null)
  const animGroupsRef = useRef<{ [key: string]: BABYLON.AnimationGroup }>({})
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null)
  const isActuallySpeaking = useRef(false)

  const startTalkingAnim = useCallback(() => {
    const groups = animGroupsRef.current
    if (groups['lipsync'] && !isActuallySpeaking.current) {
      groups['lipsync']?.play(true)
      groups['gesture']?.play(true)
      isActuallySpeaking.current = true
    }
  }, [])

  const stopTalkingAnim = useCallback(() => {
    const groups = animGroupsRef.current
    groups['lipsync']?.stop()
    groups['gesture']?.stop()
    isActuallySpeaking.current = false
  }, [])

  // Speak text using Web Speech API
  useEffect(() => {
    if (!speakText) return

    // Cancel any ongoing speech
    window.speechSynthesis.cancel()

    const utterance = new SpeechSynthesisUtterance(speakText)
    utterance.rate = 1.0
    utterance.pitch = 1.1
    utterance.volume = 1.0

    // Try to use a female English voice
    const voices = window.speechSynthesis.getVoices()
    const preferred = voices.find(
      (v) => v.name.includes('Samantha') || v.name.includes('Karen') || v.name.includes('Fiona')
    ) || voices.find(
      (v) => v.lang.startsWith('en') && v.name.toLowerCase().includes('female')
    ) || voices.find(
      (v) => v.lang.startsWith('en')
    )
    if (preferred) utterance.voice = preferred

    utterance.onstart = () => startTalkingAnim()
    utterance.onend = () => stopTalkingAnim()
    utterance.onerror = () => stopTalkingAnim()

    utteranceRef.current = utterance
    window.speechSynthesis.speak(utterance)

    return () => {
      window.speechSynthesis.cancel()
      stopTalkingAnim()
    }
  }, [speakText, startTalkingAnim, stopTalkingAnim])

  // Also respond to isSpeaking prop for manual control
  useEffect(() => {
    if (isSpeaking) {
      startTalkingAnim()
    } else if (!utteranceRef.current || !window.speechSynthesis.speaking) {
      stopTalkingAnim()
    }
  }, [isSpeaking, startTalkingAnim, stopTalkingAnim])

  useEffect(() => {
    if (!canvasRef.current) return

    const engine = new BABYLON.Engine(canvasRef.current, true, {
      preserveDrawingBuffer: true,
      stencil: true,
    })
    engineRef.current = engine

    const scene = new BABYLON.Scene(engine)
    scene.clearColor = new BABYLON.Color4(0, 0, 0, 0)

    // Camera — focused on face/upper body
    const camera = new BABYLON.ArcRotateCamera(
      'cam',
      Math.PI / 2,
      1.3,
      2.2,
      new BABYLON.Vector3(0, 1.5, 0),
      scene
    )
    camera.attachControl(canvasRef.current, false)
    camera.lowerRadiusLimit = 1.5
    camera.upperRadiusLimit = 4
    camera.wheelPrecision = 50
    camera.panningSensibility = 0

    // Lighting
    const hemiLight = new BABYLON.HemisphericLight(
      'hemi',
      new BABYLON.Vector3(0, 1, 0),
      scene
    )
    hemiLight.intensity = 0.7

    const dirLight = new BABYLON.DirectionalLight(
      'dir',
      new BABYLON.Vector3(-0.5, -1, 1),
      scene
    )
    dirLight.intensity = 0.5

    // Load character model
    BABYLON.SceneLoader.ImportMesh(
      '',
      CHARACTER_PATH,
      'cristine.gltf',
      scene,
      (_meshes, _particleSystems, _skeletons, animationGroups) => {
        animationGroups.forEach((ag) => ag.stop())

        // Load animation files
        loadAnimation(scene, 'stand_idle', ANIMATION_PATH + 'stand_idle.glb', true)
        loadAnimation(scene, 'blink', ANIMATION_PATH + 'blink.glb', true)
        loadAnimation(scene, 'face_idle', ANIMATION_PATH + 'face_idle.glb', true)
        loadAnimation(scene, 'lipsync', ANIMATION_PATH + 'lipsync.glb', false)
        loadAnimation(scene, 'gesture', ANIMATION_PATH + 'gesture.glb', false)
      },
      undefined,
      (_scene, message) => {
        console.warn('Character load error:', message)
      }
    )

    engine.runRenderLoop(() => scene.render())

    const handleResize = () => engine.resize()
    window.addEventListener('resize', handleResize)

    // Ensure voices are loaded (some browsers load async)
    window.speechSynthesis.getVoices()

    return () => {
      window.speechSynthesis.cancel()
      window.removeEventListener('resize', handleResize)
      engine.dispose()
      engineRef.current = null
      animGroupsRef.current = {}
    }
  }, [])

  function loadAnimation(
    scene: BABYLON.Scene,
    name: string,
    url: string,
    autoPlay: boolean
  ) {
    BABYLON.SceneLoader.ImportAnimations(
      url,
      '',
      scene,
      false,
      BABYLON.SceneLoaderAnimationGroupLoadingMode.NoSync,
      undefined,
      (scene) => {
        const lastGroup = scene.animationGroups[scene.animationGroups.length - 1]
        if (lastGroup) {
          animGroupsRef.current[name] = lastGroup
          if (autoPlay) {
            lastGroup.play(true)
          } else {
            lastGroup.stop()
          }
        }
      },
      undefined,
      (_scene, message) => {
        console.warn(`Animation "${name}" load error:`, message)
      }
    )
  }

  return (
    <div
      className="pointer-events-none fixed bottom-0 right-0 z-50"
      style={{ width: 380, height: 420 }}
    >
      <canvas
        ref={canvasRef}
        className="h-full w-full"
        style={{ background: 'transparent' }}
      />
    </div>
  )
}
