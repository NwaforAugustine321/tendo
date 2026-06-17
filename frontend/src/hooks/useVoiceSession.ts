import { useCallback, useEffect, useRef, useState } from 'react'
import { VoiceClient } from '../lib/voice-client'

type VoiceSessionState = 'disconnected' | 'connecting' | 'reconnecting' | 'idle' | 'listening' | 'speaking' | 'error'

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws/voice'

export function useVoiceSession() {
  const [state, setState] = useState<VoiceSessionState>('disconnected')
  const [currentResponse, setCurrentResponse] = useState('')
  const [errorMessage, setErrorMessage] = useState('')
  const [reconnectAttempt, setReconnectAttempt] = useState(0)
  const [turnComplete, setTurnComplete] = useState(false)
  const clientRef = useRef<VoiceClient | null>(null)

  const connect = useCallback(async () => {
    if (clientRef.current) return

    setState('connecting')
    setErrorMessage('')

    const client = new VoiceClient({
      onTranscript: (text) => {
        // Stream text live as it arrives (word by word)
        setCurrentResponse((prev) => prev + text)
        setTurnComplete(false)
      },
      onTurnComplete: () => {
        setTurnComplete(true)
      },
      onError: (err) => {
        setErrorMessage(err)
        setState('error')
      },
      onSpeakingStart: () => setState('speaking'),
      onSpeakingEnd: () => setState('idle'),
      onReconnecting: (attempt) => {
        setReconnectAttempt(attempt)
        setState('reconnecting')
      },
      onReconnected: () => {
        setReconnectAttempt(0)
        setState('idle')
        setErrorMessage('')
      },
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

  const stopListening = useCallback((): string | null => {
    if (!clientRef.current) return null
    const audioUrl = clientRef.current.stopMic()
    setCurrentResponse('')
    setTurnComplete(false)
    setState('idle')
    return audioUrl
  }, [])

  const sendText = useCallback((text: string) => {
    // Clear current response for new turn
    setCurrentResponse('')
    setTurnComplete(false)
    if (!clientRef.current) {
      connect().then(() => {
        clientRef.current?.sendText(text)
      })
      return
    }
    clientRef.current.sendText(text)
  }, [connect])

  const clearResponse = useCallback(() => {
    setCurrentResponse('')
    setTurnComplete(false)
  }, [])

  const disconnect = useCallback(() => {
    if (clientRef.current) {
      clientRef.current.disconnect()
      clientRef.current = null
    }
    setState('disconnected')
    setCurrentResponse('')
    setErrorMessage('')
    setReconnectAttempt(0)
    setTurnComplete(false)
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
    currentResponse,     // Live streaming text (updates word-by-word)
    turnComplete,        // True when AI finishes speaking
    errorMessage,
    reconnectAttempt,
    connect,
    startListening,
    stopListening,
    sendText,
    clearResponse,
    disconnect,
    isConnected: state === 'idle' || state === 'listening' || state === 'speaking',
    isSpeaking: state === 'speaking',
    isListening: state === 'listening',
    isReconnecting: state === 'reconnecting',
    isError: state === 'error',
  }
}
