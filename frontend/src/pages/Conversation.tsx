import { useState, useEffect } from 'react'
import { ConversationPage, type MessageItem } from '../components/conversation/ConversationPage'
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

  useEffect(() => {
    voice.connect()
    return () => voice.disconnect()
  }, [])

  // Add AI transcript as a message when turn completes
  useEffect(() => {
    if (voice.transcript) {
      const aiMsg: MessageItem = {
        id: Date.now().toString(),
        role: 'assistant',
        content: voice.transcript,
        type: 'text',
      }
      setMessages((prev) => [...prev, aiMsg])
    }
  }, [voice.transcript])

  const handleSendText = (text: string) => {
    const userMsg: MessageItem = {
      id: Date.now().toString(),
      role: 'user',
      content: text,
      type: 'text',
    }
    setMessages((prev) => [...prev, userMsg])
    voice.sendText(text)
  }

  const handleVoiceToggle = async () => {
    if (voice.isListening) {
      voice.stopListening()
    } else {
      await voice.startListening()
    }
  }

  const handleOptionSelect = (optionId: string) => {
    const userMsg: MessageItem = {
      id: Date.now().toString(),
      role: 'user',
      content: optionId,
      type: 'text',
    }
    setMessages((prev) => [...prev, userMsg])
    voice.sendText(optionId)
  }

  const handleConfirm = () => {
    setMessages((prev) => [...prev, { id: Date.now().toString(), role: 'user', content: '✓ Confirmed', type: 'text' }])
    voice.sendText('confirmed')
  }

  const handleCancel = () => {
    setMessages((prev) => [...prev, { id: Date.now().toString(), role: 'user', content: '✕ Cancelled', type: 'text' }])
    voice.sendText('cancelled')
  }

  return (
    <ConversationPage
      messages={messages}
      isTyping={voice.isSpeaking || !!voice.transcriptBuffer}
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
