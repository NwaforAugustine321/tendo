import { useCallback, useEffect, useRef, useState } from 'react'
import { VoiceClient } from '../lib/voice-client'

type VoiceSessionState = 'disconnected' | 'connecting' | 'idle' | 'listening' | 'speaking' | 'error'

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws/voice'

export function useVoiceSession() {
  const [state, setState] = useState<VoiceSessionState>('disconnected')
  const [transcript, setTranscript] = useState('')
  const [transcriptBuffer, setTranscriptBuffer] = useState('')
  const [errorMessage, setErrorMessage] = useState('')
  const clientRef = useRef<VoiceClient | null>(null)

  const connect = useCallback(async () => {
    if (clientRef.current) return

    setState('connecting')
    setErrorMessage('')

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
        setErrorMessage(err)
        setState('error')
      },
      onSpeakingStart: () => setState('speaking'),
      onSpeakingEnd: () => setState('idle'),
    })

    try {
      await client.connect(WS_URL)
      clientRef.current = client
      setState('idle')
    } catch {
      setErrorMessage('Could not connect to voice server. Make sure the backend is running.')
      setState('error')
    }
  }, [])

  const startListening = useCallback(async () => {
    // If not connected yet, connect first
    if (!clientRef.current) {
      await connect()
    }

    if (!clientRef.current) {
      setErrorMessage('Voice server not available')
      setState('error')
      return
    }

    try {
      await clientRef.current.startMic()
      setState('listening')
      setErrorMessage('')
    } catch (err: any) {
      if (err?.name === 'NotAllowedError' || err?.message?.includes('Permission')) {
        setErrorMessage('Microphone permission denied. Please allow mic access and try again.')
      } else {
        setErrorMessage('Could not access microphone. Check your browser settings.')
      }
      setState('error')
    }
  }, [connect])

  const stopListening = useCallback(() => {
    if (!clientRef.current) return
    clientRef.current.stopMic()
    setState('idle')
  }, [])

  const sendText = useCallback((text: string) => {
    if (!clientRef.current) {
      // If not connected, try connecting then send
      connect().then(() => {
        clientRef.current?.sendText(text)
      })
      return
    }
    clientRef.current.sendText(text)
  }, [connect])

  const disconnect = useCallback(() => {
    if (clientRef.current) {
      clientRef.current.disconnect()
      clientRef.current = null
    }
    setState('disconnected')
    setTranscript('')
    setTranscriptBuffer('')
    setErrorMessage('')
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
    errorMessage,
    connect,
    startListening,
    stopListening,
    sendText,
    disconnect,
    isConnected: state === 'idle' || state === 'listening' || state === 'speaking',
    isSpeaking: state === 'speaking',
    isListening: state === 'listening',
    isError: state === 'error',
  }
}
