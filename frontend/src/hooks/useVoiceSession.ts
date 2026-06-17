import { useCallback, useEffect, useRef, useState } from 'react'
import { VoiceClient } from '../lib/voice-client'

type VoiceSessionState = 'disconnected' | 'connecting' | 'idle' | 'listening' | 'speaking'

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws/voice'

export function useVoiceSession() {
  const [state, setState] = useState<VoiceSessionState>('disconnected')
  const [transcript, setTranscript] = useState('')
  const [transcriptBuffer, setTranscriptBuffer] = useState('')
  const clientRef = useRef<VoiceClient | null>(null)

  const connect = useCallback(async () => {
    if (clientRef.current) return

    setState('connecting')
    const client = new VoiceClient({
      onTranscript: (text) => {
        setTranscriptBuffer((prev) => prev + text)
      },
      onTurnComplete: () => {
        setTranscriptBuffer((prev) => {
          setTranscript(prev)
          return ''
        })
      },
      onError: (err) => {
        console.error('Voice error:', err)
        setState('disconnected')
      },
      onSpeakingStart: () => setState('speaking'),
      onSpeakingEnd: () => setState('idle'),
    })

    try {
      await client.connect(WS_URL)
      clientRef.current = client
      setState('idle')
    } catch (err) {
      console.error('Voice connect failed:', err)
      setState('disconnected')
    }
  }, [])

  const startListening = useCallback(async () => {
    if (!clientRef.current) return
    await clientRef.current.startMic()
    setState('listening')
  }, [])

  const stopListening = useCallback(() => {
    if (!clientRef.current) return
    clientRef.current.stopMic()
    setState('idle')
  }, [])

  const sendText = useCallback((text: string) => {
    if (!clientRef.current) return
    clientRef.current.sendText(text)
  }, [])

  const disconnect = useCallback(() => {
    if (clientRef.current) {
      clientRef.current.disconnect()
      clientRef.current = null
    }
    setState('disconnected')
    setTranscript('')
    setTranscriptBuffer('')
  }, [])

  useEffect(() => {
    return () => {
      if (clientRef.current) {
        clientRef.current.disconnect()
        clientRef.current = null
      }
    }
  }, [])

  return {
    state,
    transcript,
    transcriptBuffer,
    connect,
    startListening,
    stopListening,
    sendText,
    disconnect,
    isConnected: state !== 'disconnected' && state !== 'connecting',
    isSpeaking: state === 'speaking',
    isListening: state === 'listening',
  }
}
