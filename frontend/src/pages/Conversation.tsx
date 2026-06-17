import { useState, useEffect, useRef } from 'react'
import { ConversationPage, type MessageItem } from '../components/containers'
import { useVoiceSession } from '../hooks/useVoiceSession'

type Props = {
  initialMessages?: MessageItem[]
  sessionTitle?: string
  fullScreen?: boolean
  showHeader?: boolean
}

export function Conversation({ initialMessages, sessionTitle, fullScreen = false, showHeader = false }: Props) {
  const [messages, setMessages] = useState<MessageItem[]>(initialMessages ?? [])
  const voice = useVoiceSession()
  const streamingMsgId = useRef<string | null>(null)

  useEffect(() => {
    if (voice.currentResponse) {
      if (!streamingMsgId.current) {
        const id = `ai-${Date.now()}`
        streamingMsgId.current = id
        setMessages((prev) => [...prev, { id, role: 'assistant', content: voice.currentResponse, type: 'text' }])
      } else {
        const id = streamingMsgId.current
        setMessages((prev) =>
          prev.map((m) => m.id === id ? { ...m, content: voice.currentResponse } : m)
        )
      }
    }
  }, [voice.currentResponse])

  useEffect(() => {
    if (voice.turnComplete && streamingMsgId.current) {
      streamingMsgId.current = null
    }
  }, [voice.turnComplete])

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
    setMessages((prev) => [...prev, { id: Date.now().toString(), role: 'user', content: text, type: 'text' }])
    streamingMsgId.current = null
    voice.sendText(text)
  }

  const handleVoiceToggle = async () => {
    if (voice.isListening) {
      const audioUrl = await voice.stopListening()
      setMessages((prev) => [...prev, {
        id: Date.now().toString(),
        role: 'user',
        content: '🎤 Voice message',
        type: 'text',
        audioUrl: audioUrl ?? undefined,
      }])
      streamingMsgId.current = null
    } else {
      await voice.startListening()
    }
  }

  const handleOptionSelect = (optionId: string) => {
    setMessages((prev) => [...prev, { id: Date.now().toString(), role: 'user', content: optionId, type: 'text' }])
    streamingMsgId.current = null
    voice.sendText(optionId)
  }

  const handleConfirm = () => {
    setMessages((prev) => [...prev, { id: Date.now().toString(), role: 'user', content: '✓ Confirmed', type: 'text' }])
    streamingMsgId.current = null
    voice.sendText('confirmed')
  }

  const handleCancel = () => {
    setMessages((prev) => [...prev, { id: Date.now().toString(), role: 'user', content: '✕ Cancelled', type: 'text' }])
    streamingMsgId.current = null
    voice.sendText('cancelled')
  }

  return (
    <ConversationPage
      messages={messages}
      isTyping={voice.isSpeaking}
      onSendText={handleSendText}
      onVoiceRecorded={() => {}}
      onVoiceToggle={handleVoiceToggle}
      isListening={voice.isListening}
      onOptionSelect={handleOptionSelect}
      onConfirm={handleConfirm}
      onModify={() => {}}
      onCancel={handleCancel}
      onRevert={() => {}}
      onContinueFromHere={() => {}}
      showHeader={showHeader}
      headerSubtitle={sessionTitle ?? 'Your AI Business Assistant'}
      fullScreen={fullScreen}
    />
  )
}
