/**
 * Voice WebSocket client — connects browser to backend /ws/voice endpoint.
 * Handles mic capture, audio streaming, and playback.
 *
 * Protocol:
 *   Send: {type: "audio", data: base64PCM} | {type: "text", data: string}
 *   Recv: {type: "audio", data: base64PCM} | {type: "transcript", data: string} | {type: "turn_complete"}
 */

type VoiceClientCallbacks = {
  onTranscript: (text: string) => void
  onTurnComplete: () => void
  onError: (error: string) => void
  onSpeakingStart: () => void
  onSpeakingEnd: () => void
}

export class VoiceClient {
  private ws: WebSocket | null = null
  private audioContext: AudioContext | null = null
  private mediaStream: MediaStream | null = null
  private processor: ScriptProcessorNode | null = null
  private playbackQueue: ArrayBuffer[] = []
  private isPlaying = false
  private callbacks: VoiceClientCallbacks

  constructor(callbacks: VoiceClientCallbacks) {
    this.callbacks = callbacks
  }

  async connect(url: string) {
    this.audioContext = new AudioContext({ sampleRate: 24000 })
    this.ws = new WebSocket(url)

    this.ws.onmessage = (event) => {
      const msg = JSON.parse(event.data)
      this.handleMessage(msg)
    }

    this.ws.onerror = () => {
      this.callbacks.onError('Voice connection error')
    }

    this.ws.onclose = () => {
      this.stopMic()
    }

    // Wait for connection
    await new Promise<void>((resolve, reject) => {
      if (!this.ws) return reject('No WebSocket')
      this.ws.onopen = () => resolve()
      this.ws.onerror = () => reject('Connection failed')
    })
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
        if (msg.data) {
          this.callbacks.onTranscript(msg.data)
        }
        break

      case 'turn_complete':
        this.callbacks.onTurnComplete()
        // Playback will call onSpeakingEnd when queue drains
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

    // Convert Int16 PCM to Float32 for Web Audio
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

    const micContext = new AudioContext({ sampleRate: 16000 })
    const source = micContext.createMediaStreamSource(this.mediaStream)

    // Use ScriptProcessor for raw PCM access (deprecated but widely supported)
    this.processor = micContext.createScriptProcessor(4096, 1, 1)
    this.processor.onaudioprocess = (event) => {
      if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return

      const inputData = event.inputBuffer.getChannelData(0)
      const int16Data = new Int16Array(inputData.length)

      for (let i = 0; i < inputData.length; i++) {
        int16Data[i] = Math.max(-32768, Math.min(32767, inputData[i] * 32768))
      }

      const base64 = arrayBufferToBase64(int16Data.buffer)
      this.ws.send(JSON.stringify({ type: 'audio', data: base64 }))
    }

    source.connect(this.processor)
    this.processor.connect(micContext.destination)
  }

  stopMic() {
    if (this.processor) {
      this.processor.disconnect()
      this.processor = null
    }
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((t) => t.stop())
      this.mediaStream = null
    }
  }

  sendText(text: string) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'text', data: text }))
    }
  }

  disconnect() {
    this.stopMic()
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    if (this.audioContext) {
      this.audioContext.close()
      this.audioContext = null
    }
    this.playbackQueue = []
    this.isPlaying = false
  }
}

// Helpers
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
