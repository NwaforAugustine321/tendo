/**
 * Voice client — mic capture, audio playback, and voice protocol.
 */

import { WSClient } from './ws'

type VoiceCallbacks = {
  onTranscript: (text: string) => void
  onTurnComplete: () => void
  onError: (error: string) => void
  onSpeakingStart: () => void
  onSpeakingEnd: () => void
  onReconnecting?: (attempt: number) => void
  onReconnected?: () => void
  onInput?: (inputSpec: any) => void
  onMessage?: (data: any) => void
}

export class VoiceClient {
  private wsClient: WSClient | null = null
  private audioContext: AudioContext | null = null
  private micContext: AudioContext | null = null
  private mediaStream: MediaStream | null = null
  private workletNode: AudioWorkletNode | null = null
  private recorder: MediaRecorder | null = null
  private recordedChunks: Blob[] = []
  private playbackQueue: ArrayBuffer[] = []
  private isPlaying = false
  private callbacks: VoiceCallbacks
  private gestureUnlocked = false
  private gestureHandler: (() => void) | null = null

  constructor(callbacks: VoiceCallbacks) {
    this.callbacks = callbacks
  }

  async connect(url: string) {
    this.audioContext = new AudioContext({ sampleRate: 24000 })

    // If AudioContext is suspended, set up a one-time gesture listener
    if (this.audioContext.state === 'suspended') {
      this.setupGestureUnlock()
    } else {
      this.gestureUnlocked = true
    }

    // Listen for state changes (context may resume later via gesture)
    this.audioContext.onstatechange = () => {
      if (this.audioContext?.state === 'running' && !this.gestureUnlocked) {
        this.gestureUnlocked = true
        this.removeGestureListener()
        this.drainQueue()
      }
    }

    this.wsClient = new WSClient({
      onMessage: (msg) => this.handleMessage(msg),
      onError: (err) => this.callbacks.onError(err),
      onClose: () => this.stopMic(),
      onReconnecting: (attempt) => this.callbacks.onReconnecting?.(attempt),
      onReconnected: () => this.callbacks.onReconnected?.(),
    })

    await this.wsClient.connect(url)
  }

  private setupGestureUnlock() {
    this.gestureHandler = () => {
      if (this.audioContext && this.audioContext.state === 'suspended') {
        this.audioContext.resume().then(() => {
          this.gestureUnlocked = true
          this.removeGestureListener()
          this.drainQueue()
        })
      } else {
        this.gestureUnlocked = true
        this.removeGestureListener()
        this.drainQueue()
      }
    }

    const events = ['click', 'touchstart', 'keydown'] as const
    events.forEach((evt) => document.addEventListener(evt, this.gestureHandler!, { once: true }))
  }

  private removeGestureListener() {
    if (!this.gestureHandler) return
    const events = ['click', 'touchstart', 'keydown'] as const
    events.forEach((evt) => document.removeEventListener(evt, this.gestureHandler!))
    this.gestureHandler = null
  }

  private drainQueue() {
    if (this.playbackQueue.length > 0 && !this.isPlaying) {
      this.callbacks.onSpeakingStart()
      this.playNextChunk()
    }
  }

  private handleMessage(msg: { type: string; data?: any }) {
    switch (msg.type) {
      case 'message':
        if (msg.data) {
          console.log('[VoiceClient] message type received:', msg.data)
          this.callbacks.onMessage?.(msg.data)
        }
        break

      case 'audio':
        if (msg.data) {
          const pcmBytes = base64ToArrayBuffer(msg.data)
          this.playbackQueue.push(pcmBytes)

          if (this.gestureUnlocked && this.audioContext?.state === 'running') {
            if (!this.isPlaying) {
              this.callbacks.onSpeakingStart()
              this.playNextChunk()
            }
          }
        }
        break

      case 'transcript':
        if (msg.data) this.callbacks.onTranscript(msg.data)
        break

      case 'input':
        if (msg.data) this.callbacks.onInput?.(msg.data)
        break

      case 'turn_complete':
        this.callbacks.onTurnComplete()
        break

      case 'error':
        this.callbacks.onError(msg.data || 'Unknown error')
        break
    }
  }

  private async playNextChunk() {
    if (!this.audioContext || this.playbackQueue.length === 0) {
      this.isPlaying = false
      this.callbacks.onSpeakingEnd()
      return
    }

    if (this.audioContext.state === 'suspended') {
      // Can't play yet — wait for gesture
      this.isPlaying = false
      return
    }

    this.isPlaying = true
    const pcmData = this.playbackQueue.shift()!
    const int16Array = new Int16Array(pcmData)
    const float32Array = new Float32Array(int16Array.length)

    for (let i = 0; i < int16Array.length; i++) {
      float32Array[i] = int16Array[i] / 32768
    }

    const buffer = this.audioContext.createBuffer(1, float32Array.length, 24000)
    buffer.getChannelData(0).set(float32Array)

    const source = this.audioContext.createBufferSource()
    source.buffer = buffer
    source.connect(this.audioContext.destination)
    source.onended = () => this.playNextChunk()
    source.start()
  }

  async startMic() {
    this.mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        sampleRate: 16000,
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
      },
    })

    this.micContext = new AudioContext({ sampleRate: 16000 })
    const source = this.micContext.createMediaStreamSource(this.mediaStream)

    // Register AudioWorklet processor inline via Blob URL
    const processorCode = `
      class PCMProcessor extends AudioWorkletProcessor {
        process(inputs) {
          const input = inputs[0][0]
          if (input) {
            this.port.postMessage(input)
          }
          return true
        }
      }
      registerProcessor('pcm-processor', PCMProcessor)
    `
    const blob = new Blob([processorCode], { type: 'application/javascript' })
    const url = URL.createObjectURL(blob)

    await this.micContext.audioWorklet.addModule(url)
    URL.revokeObjectURL(url)

    this.workletNode = new AudioWorkletNode(this.micContext, 'pcm-processor')
    this.workletNode.port.onmessage = (event) => {
      if (!this.wsClient?.isOpen()) return

      const float32Data: Float32Array = event.data
      const int16Data = new Int16Array(float32Data.length)

      for (let i = 0; i < float32Data.length; i++) {
        int16Data[i] = Math.max(-32768, Math.min(32767, float32Data[i] * 32768))
      }

      const base64 = arrayBufferToBase64(int16Data.buffer)
      this.wsClient.send({ type: 'audio', data: base64 })
    }

    source.connect(this.workletNode)
    this.workletNode.connect(this.micContext.destination)

    // Also record locally for playback
    this.recordedChunks = []
    this.recorder = new MediaRecorder(this.mediaStream)
    this.recorder.ondataavailable = (e) => {
      if (e.data.size > 0) this.recordedChunks.push(e.data)
    }
    this.recorder.start()
  }

  stopMic(): Promise<string | null> {
    return new Promise((resolve) => {
      // Stop worklet and mic stream
      if (this.workletNode) {
        this.workletNode.disconnect()
        this.workletNode = null
      }
      if (this.micContext) {
        this.micContext.close()
        this.micContext = null
      }

      // Signal end of user turn
      this.wsClient?.send({ type: 'end_turn' })

      // Stop recorder and wait for final data
      if (this.recorder && this.recorder.state === 'recording') {
        this.recorder.onstop = () => {
          const blob = new Blob(this.recordedChunks, { type: 'audio/webm' })
          const audioUrl = URL.createObjectURL(blob)
          this.recordedChunks = []
          this.recorder = null
          resolve(audioUrl)
        }
        this.recorder.stop()
      } else {
        this.recorder = null
        this.recordedChunks = []
        resolve(null)
      }

      if (this.mediaStream) {
        this.mediaStream.getTracks().forEach((t) => t.stop())
        this.mediaStream = null
      }
    })
  }

  sendText(text: string) {
    this.wsClient?.send({ type: 'text', data: text })
  }

  disconnect() {
    this.removeGestureListener()
    this.stopMic()
    this.wsClient?.close()
    this.wsClient = null
    if (this.audioContext) {
      this.audioContext.close()
      this.audioContext = null
    }
    this.playbackQueue = []
    this.isPlaying = false
    this.gestureUnlocked = false
  }
}

function base64ToArrayBuffer(base64: string): ArrayBuffer {
  const binary = atob(base64)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i)
  }
  return bytes.buffer
}

function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer)
  let binary = ''
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i])
  }
  return btoa(binary)
}
