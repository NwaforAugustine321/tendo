import { useCallback, useEffect, useRef, useState } from 'react'
import { LiveKitVoiceClient } from '../lib/livekit-client'
import type { InputSpec } from '../components/containers/ConversationPage'
import { request } from '../lib/services/http'
import { connectSocket, disconnectSocket } from '../lib/ws'
import type { Socket } from 'socket.io-client'

type SessionState = 'disconnected' | 'connecting' | 'idle' | 'listening' | 'speaking' | 'error'

export type AgentMessage = {
  id: string
  response: string
  msgType: 'question' | 'answer'
  questions?: InputSpec
  extracted?: Record<string, string>
}

export function useVoiceSession() {
  const [state, setState] = useState<SessionState>('disconnected')
  const [lastMessage, setLastMessage] = useState<AgentMessage | null>(null)
  const [lastTranscript, setLastTranscript] = useState<string | null>(null)
  const [errorMessage, setErrorMessage] = useState('')
  const [thinkingText, setThinkingText] = useState('')
  const [thoughtText, setThoughtText] = useState('')
  const [micActive, setMicActive] = useState(false)
  const [userSpeaking, setUserSpeaking] = useState(false)
  const [agentSpeaking, setAgentSpeaking] = useState(false)
  const clientRef = useRef<LiveKitVoiceClient | null>(null)
  const socketRef = useRef<Socket | null>(null)
  const connectParamsRef = useRef<{ sessionId?: string; businessId?: string }>({})
  const msgCounter = useRef(0)

  // Socket.IO for text-only chat (fallback when LiveKit isn't used)
  const ensureSocket = useCallback((): Socket => {
    if (!socketRef.current) {
      const socket = connectSocket()
      socketRef.current = socket

      socket.on('message', (data: any) => {
        const msg = typeof data === 'string' ? JSON.parse(data) : data
        if (msg.type === 'message' && msg.data) {
          const { response, msg_type, questions, extracted } = msg.data
          msgCounter.current++
          setLastMessage({
            id: `msg-${msgCounter.current}`,
            response: response || '',
            msgType: msg_type || 'answer',
            questions: questions || undefined,
            extracted: extracted || undefined,
          })
          setThinkingText('')
          setThoughtText('')
        } else if (msg.type === 'thinking') {
          setThinkingText(msg.data || '')
        } else if (msg.type === 'thought') {
          setThoughtText(msg.data || '')
        } else if (msg.type === 'error') {
          setErrorMessage(msg.data || 'Something went wrong')
        }
      })
    }
    return socketRef.current
  }, [])

  // LiveKit connect — for voice mode
  const connect = useCallback(async (params?: { sessionId?: string; businessId?: string }) => {
    if (clientRef.current?.isConnected()) return
    if (params) connectParamsRef.current = params

    setState('connecting')

    // Always read fresh businessId from store if not provided
    const { useBusinessStore } = await import('../store/business')
    const storeBusinessId = useBusinessStore.getState().currentProfile?.id || ''
    const effectiveParams = {
      sessionId: connectParamsRef.current.sessionId || '',
      businessId: connectParamsRef.current.businessId || storeBusinessId,
    }

    if (!effectiveParams.businessId) {
      setErrorMessage('No business profile selected.')
      return
    }

    // Get user_id from auth store
    const { useAuthStore } = await import('../store/auth')
    const userId = useAuthStore.getState().user?.user_id || ''

    if (!userId) {
      setErrorMessage('Authentication required. Please log in.')
      return
    }

    setErrorMessage('')

    try {
      const tokenResponse = await request<{ token: string; url: string; room: string }>('/voice/token', {
        method: 'POST',
        body: {
          session_id: effectiveParams.sessionId,
          business_id: effectiveParams.businessId,
          user_id: userId,
        },
        silent: true,
      })

      const client = new LiveKitVoiceClient({
        onConnected: () => {
          setState('connecting')
        },
        onAgentReady: () => {
          client.startMic().then(() => {
            setMicActive(true)
            setState('listening')
          }).catch(() => {})
        },
        onDisconnected: () => {
          setState('idle')
          setMicActive(false)
          setAgentSpeaking(false)
          setUserSpeaking(false)
        },
        onUserSpeakingChange: (speaking) => setUserSpeaking(speaking),
        onAgentSpeakingChange: (speaking) => {
          setAgentSpeaking(speaking)
          if (speaking) setState('speaking')
          else setState('listening')
        },
        onMessage: (data) => {
          const { response, msg_type, questions, extracted } = data
          msgCounter.current++
          setLastMessage({
            id: `msg-${msgCounter.current}`,
            response: response || '',
            msgType: msg_type || 'answer',
            questions: questions || undefined,
            extracted: extracted || undefined,
          })
          setThinkingText('')
          setThoughtText('')
        },
        onThinking: (text) => setThinkingText(text),
        onTranscript: (text) => setLastTranscript(text),
        onTurnComplete: () => {
          setAgentSpeaking(false)
          setState('listening')
        },
        onError: (err) => {
          setErrorMessage(err)
          setState('error')
        },
      })

      await client.connect(tokenResponse.url, tokenResponse.token)
      client.setReconnectHandler(() => {
        client.disconnect()
        clientRef.current = null
        connect(connectParamsRef.current)
      })
      clientRef.current = client
      setState('idle')
    } catch {
      setState('idle')
      setErrorMessage('Voice not available. Check LiveKit configuration.')
    }
  }, [])

  const startListening = useCallback(async () => {
    if (!clientRef.current?.isConnected()) {
      await connect(connectParamsRef.current)
    }
    if (!clientRef.current?.isConnected()) {
      setErrorMessage('Voice not available.')
      setState('error')
      return
    }
    if (!clientRef.current?.isAgentReady()) {
      setErrorMessage('Agent is connecting. Please wait.')
      return
    }
    try {
      await clientRef.current.startMic()
      setMicActive(true)
      setState('listening')
      setErrorMessage('')
    } catch (err: any) {
      if (err?.name === 'NotAllowedError') {
        setErrorMessage('Microphone permission denied.')
      } else {
        setErrorMessage('Could not access microphone.')
      }
      setState('error')
    }
  }, [connect])

  const stopListening = useCallback(async (): Promise<string | null> => {
    if (clientRef.current) {
      clientRef.current.stopMic()
    }
    setMicActive(false)
    setState('idle')
    return null
  }, [])

  const sendText = useCallback((text: string, scope?: string, businessId?: string, recordId?: string, sessionId?: string) => {
    setLastMessage(null)
    setThinkingText('')
    setThoughtText('')

    // Always use Socket.IO for text chat
    const socket = ensureSocket()
    socket.emit('message', {
      type: 'text',
      data: text,
      scope: scope || null,
      record_id: recordId || '',
      business_id: businessId || '',
      session_id: sessionId || '',
    })
  }, [ensureSocket])

  const disconnect = useCallback(() => {
    clientRef.current?.disconnect()
    clientRef.current = null
    if (socketRef.current) {
      disconnectSocket()
      socketRef.current = null
    }
    setMicActive(false)
    setState('disconnected')
    setLastMessage(null)
    setErrorMessage('')
    setUserSpeaking(false)
    setAgentSpeaking(false)
  }, [])

  // Auto-connect socket for text messaging
  useEffect(() => {
    ensureSocket()
    setState('idle')
    return () => {
      clientRef.current?.disconnect()
      clientRef.current = null
      if (socketRef.current) {
        disconnectSocket()
        socketRef.current = null
      }
    }
  }, [])

  return {
    state,
    lastMessage,
    lastTranscript,
    errorMessage,
    thinkingText,
    thoughtText,
    userSpeaking,
    agentSpeaking,
    connect,
    startListening,
    stopListening,
    sendText,
    disconnect,
    isConnected: state === 'idle' || state === 'listening' || state === 'speaking',
    isSpeaking: agentSpeaking,
    isListening: micActive,
    isError: state === 'error',
    turnComplete: !agentSpeaking,
  }
}
