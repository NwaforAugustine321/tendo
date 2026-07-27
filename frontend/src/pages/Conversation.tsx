import { useState, useEffect, useRef } from 'react'
import { ConversationPage, type MessageItem } from '../components/containers'
import type { InputSpec } from '../components/containers/ConversationPage'
import { useVoiceSession } from '../hooks/useVoiceSession'
import { useBusinessStore } from '../store/business'
import { useWorkspaceStore } from '../store/workspace'
import { resumeSession } from '../lib/services/business'

type Props = {
  initialMessages?: MessageItem[]
  sessionTitle?: string
  sessionId?: string
  fullScreen?: boolean
  showHeader?: boolean
  transparentBg?: boolean
  flipCharacter?: boolean
  characterRightOffset?: number
}

export function Conversation({ initialMessages, sessionTitle, sessionId, fullScreen = false, showHeader = false, transparentBg = false, flipCharacter = false, characterRightOffset = 0 }: Props) {
  const [messages, setMessages] = useState<MessageItem[]>(initialMessages ?? [])
  const [thinking, setThinking] = useState(false)
  const [wakeActive, setWakeActive] = useState(false)
  const { currentProfile } = useBusinessStore()
  const voice = useVoiceSession()

  // Sync initialMessages when they change (e.g., switching sessions)
  useEffect(() => {
    if (initialMessages) {
      setMessages(initialMessages)
    }
  }, [initialMessages])
  const connected = useRef(false)
  const lastMsgId = useRef('')
  const currentBusinessId = useRef<string | null>(null)

  // Voice connection disabled for now
  // Connect/reconnect when profile or session changes
  // useEffect(() => {
  //   const businessId = currentProfile?.id || ''
  //   if (!businessId) return
  //   if (connected.current) {
  //     voice.disconnect()
  //     setThinking(false)
  //     connected.current = false
  //   }
  //   currentBusinessId.current = businessId
  //   if (sessionId) {
  //     connected.current = true
  //     voice.connect({ sessionId, businessId })
  //   } else {
  //     resumeSession(businessId).then(({ session_id }) => {
  //       connected.current = true
  //       voice.connect({ sessionId: session_id, businessId })
  //     }).catch((err) => {
  //       console.error('Failed to resume session:', err)
  //       connected.current = true
  //       voice.connect({ businessId })
  //     })
  //   }
  //   navigator.mediaDevices.getUserMedia({ audio: true }).catch(() => {})
  // }, [currentProfile?.id, sessionId])

  // Listen for voice toggle from the insights big mic circle
  useEffect(() => {
    const handleVoiceToggleEvent = async () => {
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
        if (!voice.isConnected) {
          await voice.connect()
        }
        await voice.startListening()
      }
      window.dispatchEvent(new CustomEvent('tendo:recording-state', {
        detail: { recording: !voice.isListening }
      }))
    }
    window.addEventListener('tendo:voice-toggle', handleVoiceToggleEvent)
    return () => window.removeEventListener('tendo:voice-toggle', handleVoiceToggleEvent)
  }, [voice.isListening, voice.isConnected])

  // When voice connects successfully, mark as active
  useEffect(() => {
    if (voice.isConnected) {
      setWakeActive(true)
    } else if (!voice.isSpeaking && !voice.isListening) {
      setWakeActive(false)
    }
  }, [voice.isConnected, voice.isSpeaking, voice.isListening])

  // Show thinking indicator when backend sends thinking event (voice transcription processing)
  useEffect(() => {
    if (voice.thinkingText) {
      setThinking(true)
    }
  }, [voice.thinkingText])

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

    let sendText: string
    if (optionContext) {
      sendText = `label: ${optionContext.label}, answer: ${optionContext.id}, description: ${optionContext.description || ''}`
    } else {
      // Check if there's a pending question — format as reply to that question
      const pendingQuestion = findPendingQuestion()
      if (pendingQuestion) {
        sendText = `${pendingQuestion}: ${text}`
      } else {
        sendText = text
      }
    }

    setMessages((prev) => [...prev, { id: `user-${Date.now()}`, role: 'user', content: displayText, type: 'text' }])
    setThinking(true)
    voice.sendText(sendText)
  }

  const pendingMsg = useWorkspaceStore((s) => s.pendingChatMessage)
  const pendingSentRef = useRef<string | null>(null)

  useEffect(() => {
    if (pendingMsg && pendingMsg !== pendingSentRef.current) {
      // Wait for voice to be connected before sending
      if (!voice.isConnected) {
        const interval = setInterval(() => {
          if (voice.isConnected) {
            clearInterval(interval)
            pendingSentRef.current = pendingMsg
            handleSendText(pendingMsg)
            useWorkspaceStore.getState().setPendingChatMessage(null)
          }
        }, 200)
        // Timeout after 5s
        setTimeout(() => clearInterval(interval), 5000)
        return () => clearInterval(interval)
      }
      pendingSentRef.current = pendingMsg
      handleSendText(pendingMsg)
      useWorkspaceStore.getState().setPendingChatMessage(null)
    }
  }, [pendingMsg, voice.isConnected])

  const findPendingQuestion = (): string | null => {
    for (let i = messages.length - 1; i >= 0; i--) {
      const msg = messages[i]
      if (msg.role === 'user') break
      if (msg.type === 'input' && msg.inputSpec?.fields) {
        const field = msg.inputSpec.fields[0]
        if (field.type === 'text') {
          return field.description || field.name || null
        }
        if (field.type === 'radio') {
          return field.options?.[0]?.name || null
        }
      }
    }
    return null
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
      thinkingText={thinking ? (voice.thinkingText || 'Thinking...') : undefined}
      thoughtText={thinking ? voice.thoughtText : undefined}
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
