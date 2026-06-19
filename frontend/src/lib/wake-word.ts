/**
 * Wake Word Listener using Vosk WebAssembly for offline speech recognition.
 * Continuously listens for a configurable wake phrase locally.
 * Zero network usage while idle.
 */

import { createModel, type KaldiRecognizer, type Model } from 'vosk-browser'

const WAKE_PHRASES = (import.meta.env.VITE_WAKE_PHRASE)
  .toLowerCase()
  .split(',')
  .map((p: string) => p.trim())
  .filter(Boolean)
const MODEL_PATH = import.meta.env.VITE_VOSK_MODEL_PATH || '/models/vosk-model-small-en-us-0.15.zip'

type WakeWordCallbacks = {
  onWakeWord: (transcript: string) => void
  onError?: (error: string) => void
  onReady?: () => void
}

function matchesWakePhrase(text: string): boolean {
  return WAKE_PHRASES.some((phrase) => text.includes(phrase))
}

export class WakeWordListener {
  private model: Model | null = null
  private recognizer: KaldiRecognizer | null = null
  private audioContext: AudioContext | null = null
  private mediaStream: MediaStream | null = null
  private callbacks: WakeWordCallbacks
  private running = false

  constructor(callbacks: WakeWordCallbacks) {
    this.callbacks = callbacks
  }

  async start() {
    if (this.running) return

    try {
      if (!this.model) {
        console.log('[WakeWord] Loading model...')
        this.model = await createModel(MODEL_PATH)
        console.log('[WakeWord] Model loaded')
      }

      const sampleRate = 16000
      this.recognizer = new this.model.KaldiRecognizer(sampleRate)

      this.recognizer.on('result', (event: any) => {
        const text = (event.result?.text || '').toLowerCase().trim()
        if (text) console.log('[WakeWord] result:', text)
        if (text && matchesWakePhrase(text)) {
          console.log('[WakeWord] WAKE WORD DETECTED:', text)
          this.callbacks.onWakeWord(text)
        }
      })

    
      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
      })

      this.audioContext = new AudioContext({ sampleRate })
      const source = this.audioContext.createMediaStreamSource(this.mediaStream)

      // Feed audio to recognizer via ScriptProcessorNode
      const processor = this.audioContext.createScriptProcessor(8192, 1, 1)
      source.connect(processor)
      processor.connect(this.audioContext.destination)

      processor.addEventListener('audioprocess', (event) => {
        if (!this.running || !this.recognizer) return
        try {
          // acceptWaveform takes AudioBuffer in vosk-browser
          this.recognizer.acceptWaveform(event.inputBuffer)
        } catch {
          // Ignore
        }
      })

      this.running = true
      console.log('[WakeWord] Listening for:', WAKE_PHRASES.join(' | '))
      this.callbacks.onReady?.()
    } catch (err: any) {
      console.error('[WakeWord] Error:', err)
      this.callbacks.onError?.(err.message || 'Failed to start wake word listener')
    }
  }

  stop() {
    this.running = false

    if (this.audioContext) {
      this.audioContext.close()
      this.audioContext = null
    }
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((t) => t.stop())
      this.mediaStream = null
    }
    this.recognizer = null
    console.log('[WakeWord] Stopped')
  }

  isRunning() {
    return this.running
  }
}
