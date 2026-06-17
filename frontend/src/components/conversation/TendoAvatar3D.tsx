import { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import * as THREE from 'three'

type AvatarState = 'idle' | 'talking' | 'thinking'

/**
 * Stylized 3D animated avatar for Tendo.
 * A spherical character head with animated eyes and mouth.
 * States: idle (gentle bob + blink), talking (mouth animates), thinking (eyes look around).
 *
 * Later: replace with a Ready Player Me GLB model + Mixamo animations + lip-sync.
 */
function AvatarHead({ state }: { state: AvatarState }) {
  const groupRef = useRef<THREE.Group>(null)
  const mouthRef = useRef<THREE.Mesh>(null)
  const leftEyeRef = useRef<THREE.Mesh>(null)
  const rightEyeRef = useRef<THREE.Mesh>(null)
  const leftBrowRef = useRef<THREE.Mesh>(null)
  const rightBrowRef = useRef<THREE.Mesh>(null)

  // Blink timing
  const blinkTimer = useRef(0)
  const isBlinking = useRef(false)

  useFrame((_, delta) => {
    if (!groupRef.current) return

    // Gentle idle bob
    groupRef.current.rotation.z = Math.sin(Date.now() * 0.001) * 0.03
    groupRef.current.position.y = Math.sin(Date.now() * 0.0015) * 0.05

    // Blink logic
    blinkTimer.current += delta
    if (!isBlinking.current && blinkTimer.current > 2 + Math.random() * 3) {
      isBlinking.current = true
      blinkTimer.current = 0
    }
    if (isBlinking.current && blinkTimer.current > 0.15) {
      isBlinking.current = false
      blinkTimer.current = 0
    }

    // Eye scale for blink
    const eyeScaleY = isBlinking.current ? 0.1 : 1
    if (leftEyeRef.current) leftEyeRef.current.scale.y = THREE.MathUtils.lerp(leftEyeRef.current.scale.y, eyeScaleY, 0.3)
    if (rightEyeRef.current) rightEyeRef.current.scale.y = THREE.MathUtils.lerp(rightEyeRef.current.scale.y, eyeScaleY, 0.3)

    // Talking mouth animation
    if (mouthRef.current) {
      if (state === 'talking') {
        const mouthOpen = 0.08 + Math.sin(Date.now() * 0.012) * 0.04 + Math.sin(Date.now() * 0.019) * 0.03
        mouthRef.current.scale.y = THREE.MathUtils.lerp(mouthRef.current.scale.y, 1 + mouthOpen * 8, 0.15)
        mouthRef.current.scale.x = THREE.MathUtils.lerp(mouthRef.current.scale.x, 1 - mouthOpen * 2, 0.15)
      } else {
        mouthRef.current.scale.y = THREE.MathUtils.lerp(mouthRef.current.scale.y, 1, 0.1)
        mouthRef.current.scale.x = THREE.MathUtils.lerp(mouthRef.current.scale.x, 1, 0.1)
      }
    }

    // Thinking — eyes look around
    if (state === 'thinking') {
      const lookX = Math.sin(Date.now() * 0.002) * 0.02
      if (leftEyeRef.current) leftEyeRef.current.position.x = -0.18 + lookX
      if (rightEyeRef.current) rightEyeRef.current.position.x = 0.18 + lookX
    } else {
      if (leftEyeRef.current) leftEyeRef.current.position.x = THREE.MathUtils.lerp(leftEyeRef.current.position.x, -0.18, 0.05)
      if (rightEyeRef.current) rightEyeRef.current.position.x = THREE.MathUtils.lerp(rightEyeRef.current.position.x, 0.18, 0.05)
    }

    // Brow raise when talking
    const browY = state === 'talking' ? 0.32 : 0.28
    if (leftBrowRef.current) leftBrowRef.current.position.y = THREE.MathUtils.lerp(leftBrowRef.current.position.y, browY, 0.05)
    if (rightBrowRef.current) rightBrowRef.current.position.y = THREE.MathUtils.lerp(rightBrowRef.current.position.y, browY, 0.05)
  })

  const skinColor = useMemo(() => new THREE.Color('#d4a574'), [])
  const hairColor = useMemo(() => new THREE.Color('#3d2b1f'), [])
  const eyeColor = useMemo(() => new THREE.Color('#1a1a1a'), [])
  const mouthColor = useMemo(() => new THREE.Color('#8b3a3a'), [])
  const browColor = useMemo(() => new THREE.Color('#3d2b1f'), [])

  return (
    <group ref={groupRef}>
      {/* Head */}
      <mesh>
        <sphereGeometry args={[0.55, 32, 32]} />
        <meshStandardMaterial color={skinColor} roughness={0.7} />
      </mesh>

      {/* Hair top */}
      <mesh position={[0, 0.35, 0]}>
        <sphereGeometry args={[0.48, 32, 16, 0, Math.PI * 2, 0, Math.PI * 0.5]} />
        <meshStandardMaterial color={hairColor} roughness={0.9} />
      </mesh>

      {/* Hair sides */}
      <mesh position={[-0.4, -0.1, 0]}>
        <capsuleGeometry args={[0.12, 0.5, 8, 16]} />
        <meshStandardMaterial color={hairColor} roughness={0.9} />
      </mesh>
      <mesh position={[0.4, -0.1, 0]}>
        <capsuleGeometry args={[0.12, 0.5, 8, 16]} />
        <meshStandardMaterial color={hairColor} roughness={0.9} />
      </mesh>

      {/* Left eye */}
      <mesh ref={leftEyeRef} position={[-0.18, 0.08, 0.48]}>
        <sphereGeometry args={[0.07, 16, 16]} />
        <meshStandardMaterial color={eyeColor} />
      </mesh>

      {/* Right eye */}
      <mesh ref={rightEyeRef} position={[0.18, 0.08, 0.48]}>
        <sphereGeometry args={[0.07, 16, 16]} />
        <meshStandardMaterial color={eyeColor} />
      </mesh>

      {/* Eye whites */}
      <mesh position={[-0.18, 0.08, 0.45]}>
        <sphereGeometry args={[0.1, 16, 16]} />
        <meshStandardMaterial color="white" />
      </mesh>
      <mesh position={[0.18, 0.08, 0.45]}>
        <sphereGeometry args={[0.1, 16, 16]} />
        <meshStandardMaterial color="white" />
      </mesh>

      {/* Eyebrows */}
      <mesh ref={leftBrowRef} position={[-0.18, 0.28, 0.47]} rotation={[0, 0, 0.15]}>
        <capsuleGeometry args={[0.02, 0.1, 4, 8]} />
        <meshStandardMaterial color={browColor} />
      </mesh>
      <mesh ref={rightBrowRef} position={[0.18, 0.28, 0.47]} rotation={[0, 0, -0.15]}>
        <capsuleGeometry args={[0.02, 0.1, 4, 8]} />
        <meshStandardMaterial color={browColor} />
      </mesh>

      {/* Nose */}
      <mesh position={[0, -0.02, 0.52]}>
        <sphereGeometry args={[0.04, 8, 8]} />
        <meshStandardMaterial color={skinColor} roughness={0.6} />
      </mesh>

      {/* Mouth */}
      <mesh ref={mouthRef} position={[0, -0.15, 0.48]}>
        <capsuleGeometry args={[0.025, 0.08, 4, 8]} />
        <meshStandardMaterial color={mouthColor} />
      </mesh>
    </group>
  )
}

type Props = {
  state?: AvatarState
  size?: number
}

export function TendoAvatar3D({ state = 'idle', size = 200 }: Props) {
  return (
    <div style={{ width: size, height: size }} className="mx-auto">
      <Canvas
        camera={{ position: [0, 0, 2], fov: 40 }}
        style={{ background: 'transparent' }}
        gl={{ alpha: true, antialias: true }}
      >
        <ambientLight intensity={0.6} />
        <directionalLight position={[2, 3, 5]} intensity={0.8} />
        <directionalLight position={[-2, 1, 3]} intensity={0.3} />
        <AvatarHead state={state} />
      </Canvas>
    </div>
  )
}
