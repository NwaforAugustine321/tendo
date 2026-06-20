import { useState, useEffect, useRef } from 'react'
import { ConversationPage, type MessageItem } from '../components/containers'
import type { InputSpec } from '../components/containers/ConversationPage'
import { useVoiceSession } from '../hooks/useVoiceSession'
import { useBusinessStore } from '../store/business'
import { resumeSession } from '../lib/services/business'

type Props = {
  initialMessages?: MessageItem[]
  sessionTitle?: string
  fullScreen?: boolean
  showHeader?: boolean
  transparentBg?: boolean
  flipCharacter?: boolean
  characterRightOffset?: number
}

export function Conversation({ initialMessages, sessionTitle, fullScreen = false, showHeader = false, transparentBg = false, flipCharacter = false, characterRightOffset = 0 }: Props) {
  const [messages, setMessages] = useState<MessageItem[]>(initialMessages ?? [])
  const [thinking, setThinking] = useState(true)
  const [wakeActive, setWakeActive] = useState(false)
  const { currentProfile } = useBusinessStore()
  const voice = useVoiceSession()
  const connected = useRef(false)
  const lastMsgId = useRef('')
  const currentBusinessId = useRef<string | null>(null)

  // Connect/reconnect when profile changes
  useEffect(() => {
    const businessId = currentProfile?.id || ''
    if (!businessId) return

    // If same business, don't reconnect
    if (currentBusinessId.current === businessId && connected.current) return

    currentBusinessId.current = businessId

    // Disconnect existing session
    if (connected.current) {
      voice.disconnect()
      setMessages([])
      setThinking(true)
      connected.current = false
    }

    // Get or create a session for this business and connect
    resumeSession(businessId).then(({ session_id }) => {
      connected.current = true
      voice.connect({ sessionId: session_id, businessId })
    }).catch((err) => {
      console.error('Failed to resume session:', err)
      // Fallback: connect without session_id
      connected.current = true
      voice.connect({ businessId })
    })

    navigator.mediaDevices.getUserMedia({ audio: true }).catch(() => {})
  }, [currentProfile?.id])

  // When voice connects successfully, mark as active
  useEffect(() => {
    if (voice.isConnected) {
      setWakeActive(true)
    } else if (!voice.isSpeaking && !voice.isListening) {
      setWakeActive(false)
    }
  }, [voice.isConnected, voice.isSpeaking, voice.isListening])

  // Display agent messages when they arrive
  useEffect(() => {
    if (!voice.lastMessage) return
    if (voice.lastMessage.id === lastMsgId.current) return
    lastMsgId.current = voice.lastMessage.id
    setThinking(false)

    console.log('[Conversation] lastMessage:', voice.lastMessage)

    const { response, msgType, questions } = voice.lastMessage

    // Add the text response as a message bubble
    if (response) {
      setMessages((prev) => [...prev, {
        id: `text-${voice.lastMessage!.id}`,
        role: 'assistant',
        content: response,
        type: 'text',
      }])
    }

    // If type is "question", add the input card below the text
    if (msgType === 'question' && questions) {
      setMessages((prev) => [...prev, {
        id: `input-${voice.lastMessage!.id}`,
        role: 'assistant',
        content: '',
        type: 'input',
        inputSpec: questions as InputSpec,
      }])
    }
  }, [voice.lastMessage])

  useEffect(() => {
    if (voice.errorMessage) {
      setMessages((prev) => [...prev, {
        id: `err-${Date.now()}`,
        role: 'assistant',
        content: voice.errorMessage,
        type: 'text',
      }])
    }
  }, [voice.errorMessage])

  const handleSendText = (text: string) => {
    // Find option context if this was a radio select
    const optionContext = findOptionContext(text)
    const displayText = optionContext?.label || text
    const sendText = optionContext
      ? `label: ${optionContext.label}, answer: ${optionContext.id}, description: ${optionContext.description || ''}`
      : text

    setMessages((prev) => [...prev, { id: `user-${Date.now()}`, role: 'user', content: displayText, type: 'text' }])
    setThinking(true)
    voice.sendText(sendText)
  }

  const handleVoiceToggle = async () => {
    if (voice.isListening) {
      const audioUrl = await voice.stopListening()
      setMessages((prev) => [...prev, {
        id: `user-${Date.now()}`,
        role: 'user',
        content: '🎤 Voice message',
        type: 'text',
        audioUrl: audioUrl ?? undefined,
      }])
    } else {
      // Connect Gemini if not already connected
      if (!voice.isConnected) {
        await voice.connect()
      }
      await voice.startListening()
    }
  }

  const handleOptionSelect = (optionId: string) => {
    handleSendText(optionId)
  }

  const findOptionContext = (optionId: string): { id: string; name: string; label: string; description?: string } | null => {
    for (let i = messages.length - 1; i >= 0; i--) {
      const msg = messages[i]
      if (msg.type === 'input' && msg.inputSpec?.fields) {
        for (const field of msg.inputSpec.fields) {
          if (field.type === 'radio' && field.options) {
            const found = field.options.find((o) => o.id === optionId)
            if (found) return found
          }
        }
      }
    }
    return null
  }

  return (
    <ConversationPage
      messages={messages}
      isTyping={thinking || voice.isSpeaking}
      thinkingText={thinking ? `${import.meta.env.VITE_AGENT_NAME || 'Jay'} is processing your request` : undefined}
      onSendText={handleSendText}
      onVoiceRecorded={() => {}}
      onVoiceToggle={handleVoiceToggle}
      isListening={voice.isListening}
      onOptionSelect={handleOptionSelect}
      onConfirm={() => handleOptionSelect('confirm')}
      onModify={() => {}}
      onCancel={() => handleOptionSelect('cancel')}
      onRevert={() => {}}
      onContinueFromHere={() => {}}
      showHeader={showHeader}
      headerSubtitle={sessionTitle ?? 'Your AI Business Assistant'}
      fullScreen={fullScreen}
      transparentBg={transparentBg}
      flipCharacter={flipCharacter}
      characterRightOffset={characterRightOffset}
      wakeActive={wakeActive}
      onWakeToggle={async () => {
        if (wakeActive) {
          // Turn off: stop mic + disconnect Gemini
          await voice.stopListening()
          voice.disconnect()
          setWakeActive(false)
        } else {
          // Turn on: connect Gemini + start mic (continuous listening)
          await voice.connect()
          await voice.startListening()
          setWakeActive(true)
        }
      }}
    />
  )
}
