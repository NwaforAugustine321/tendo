/**
 * Voice client — manages mic capture, audio playback, and voice WebSocket protocol.
 * Uses AudioWorkletNode for mic capture (no deprecated ScriptProcessorNode).
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
}

export class VoiceClient {
  private wsClient: WSClient | null = null
  private audioContext: AudioContext | null = null
  private micContext: AudioContext | null = null
  private mediaStream: MediaStream | null = null
  private workletNode: AudioWorkletNode | null = null
  private playbackQueue: ArrayBuffer[] = []
  private isPlaying = false
  private callbacks: VoiceCallbacks

  constructor(callbacks: VoiceCallbacks) {
    this.callbacks = callbacks
  }

  async connect(url: string) {
    this.audioContext = new AudioContext({ sampleRate: 24000 })

    this.wsClient = new WSClient({
      onMessage: (msg) => this.handleMessage(msg),
      onError: (err) => this.callbacks.onError(err),
      onClose: () => this.stopMic(),
      onReconnecting: (attempt) => this.callbacks.onReconnecting?.(attempt),
      onReconnected: () => this.callbacks.onReconnected?.(),
    })

    await this.wsClient.connect(url)
  }

  private handleMessage(msg: { type: string; data?: string }) {
    switch (msg.type) {
      case 'audio':
        if (msg.data) {
          const pcmBytes = base64ToArrayBuffer(msg.data)
          this.playbackQueue.push(pcmBytes)
          if (!this.isPlaying) {
            this.callbacks.onSpeakingStart()
            this.playNextChunk()
          }
        }
        break

      case 'transcript':
        if (msg.data) this.callbacks.onTranscript(msg.data)
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
  }

  stopMic() {
    if (this.workletNode) {
      this.workletNode.disconnect()
      this.workletNode = null
    }
    if (this.micContext) {
      this.micContext.close()
      this.micContext = null
    }
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((t) => t.stop())
      this.mediaStream = null
    }
    // Signal end of user turn so AI knows to respond
    this.wsClient?.send({ type: 'end_turn' })
  }

  sendText(text: string) {
    this.wsClient?.send({ type: 'text', data: text })
  }

  disconnect() {
    this.stopMic()
    this.wsClient?.close()
    this.wsClient = null
    if (this.audioContext) {
      this.audioContext.close()
      this.audioContext = null
    }
    this.playbackQueue = []
    this.isPlaying = false
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
