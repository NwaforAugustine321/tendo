import { useCallback, useEffect, useRef, useState } from 'react'
import { VoiceClient } from '../lib/voice-client'
import type { InputSpec } from '../components/containers/ConversationPage'

type VoiceSessionState = 'disconnected' | 'connecting' | 'reconnecting' | 'idle' | 'listening' | 'speaking' | 'error'

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws/voice'

export type AgentMessage = {
  id: string
  response: string
  msgType: 'question' | 'answer'
  questions?: InputSpec
  extracted?: Record<string, string>
}

export function useVoiceSession() {
  const [state, setState] = useState<VoiceSessionState>('disconnected')
  const [lastMessage, setLastMessage] = useState<AgentMessage | null>(null)
  const [errorMessage, setErrorMessage] = useState('')
  const [thinkingText, setThinkingText] = useState('')
  const [reconnectAttempt, setReconnectAttempt] = useState(0)
  const [turnComplete, setTurnComplete] = useState(false)
  const clientRef = useRef<VoiceClient | null>(null)
  const msgCounter = useRef(0)

  const connect = useCallback(async (params?: { sessionId?: string; businessId?: string }) => {
    if (clientRef.current) return

    setState('connecting')
    setErrorMessage('')

    // Build WS URL with optional session params
    let wsUrl = WS_URL
    const queryParts: string[] = []
    if (params?.sessionId) queryParts.push(`session_id=${params.sessionId}`)
    if (params?.businessId) queryParts.push(`business_id=${params.businessId}`)
    if (queryParts.length > 0) {
      wsUrl += (wsUrl.includes('?') ? '&' : '?') + queryParts.join('&')
    }

    const client = new VoiceClient({
      onTranscript: (text) => {
        // This fires from the 'message' event with the full response text
        msgCounter.current++
        setLastMessage((prev) => ({
          id: `msg-${msgCounter.current}`,
          response: text,
          msgType: prev?.msgType || 'answer',
          questions: prev?.questions,
        }))
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
      onThinking: (text) => setThinkingText(text),
      onReconnecting: (attempt) => {
        setReconnectAttempt(attempt)
        setState('reconnecting')
      },
      onReconnected: () => {
        setReconnectAttempt(0)
        setState('idle')
        setErrorMessage('')
      },
      onInput: (inputSpec) => {
        msgCounter.current++
        setLastMessage({
          id: `msg-${msgCounter.current}`,
          response: '',
          msgType: 'question',
          questions: inputSpec,
        })
      },
      onMessage: (data) => {
        console.log('[VoiceSession] message received:', JSON.stringify(data))
        const { response, msg_type, questions, extracted } = data
        msgCounter.current++
        setLastMessage({
          id: `msg-${msgCounter.current}`,
          response: response || '',
          msgType: msg_type || 'answer',
          questions: questions || undefined,
          extracted: extracted || undefined,
        })
        setTurnComplete(false)
      },
    })

    try {
      await client.connect(wsUrl)
      clientRef.current = client
      setState('idle')
    } catch {
      setErrorMessage('Could not connect to voice server. Make sure the backend is running.')
      setState('error')
    }
  }, [])

  const startListening = useCallback(async () => {
    if (!clientRef.current) await connect()
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
        setErrorMessage('Microphone permission denied.')
      } else {
        setErrorMessage('Could not access microphone.')
      }
      setState('error')
    }
  }, [connect])

  const stopListening = useCallback(async (): Promise<string | null> => {
    if (!clientRef.current) return null
    const audioUrl = await clientRef.current.stopMic()
    setState('idle')
    return audioUrl
  }, [])

  const sendText = useCallback((text: string) => {
    setLastMessage(null)
    setTurnComplete(false)
    if (!clientRef.current) {
      connect().then(() => clientRef.current?.sendText(text))
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
    setLastMessage(null)
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
    lastMessage,
    turnComplete,
    errorMessage,
    thinkingText,
    reconnectAttempt,
    connect,
    startListening,
    stopListening,
    sendText,
    disconnect,
    isConnected: state === 'idle' || state === 'listening' || state === 'speaking',
    isSpeaking: state === 'speaking',
    isListening: state === 'listening',
    isReconnecting: state === 'reconnecting',
    isError: state === 'error',
  }
}
