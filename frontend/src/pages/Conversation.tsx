import { useState } from 'react'
import { ConversationPage, type MessageItem } from '../components/conversation/ConversationPage'

type Props = {
  /** Initial messages to seed the conversation (e.g., onboarding welcome) */
  initialMessages?: MessageItem[]
  /** Session title shown in header subtitle */
  sessionTitle?: string
  /** Full-screen mode (onboarding) vs embedded in workspace */
  fullScreen?: boolean
  /** Show the Tendo header */
  showHeader?: boolean
}

/**
 * Unified conversation page — used for onboarding AND ongoing business sessions.
 * The page is the same; only the initial messages and context differ.
 */
export function Conversation({ initialMessages, sessionTitle, fullScreen = false, showHeader = false }: Props) {
  const [messages, setMessages] = useState<MessageItem[]>(
    initialMessages ?? []
  )
  const [isTyping, setIsTyping] = useState(false)

  const addUserMessage = (content: string) => {
    const msg: MessageItem = {
      id: Date.now().toString(),
      role: 'user',
      content,
      type: 'text',
    }
    setMessages((prev) => [...prev, msg])
    return msg
  }

  const simulateAIResponse = (response: MessageItem) => {
    setIsTyping(true)
    setTimeout(() => {
      setIsTyping(false)
      setMessages((prev) => [...prev, response])
    }, 1200 + Math.random() * 800)
  }

  const handleSendText = (text: string) => {
    addUserMessage(text)
    // In production this calls POST /events — for now simulate
    simulateAIResponse({
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: `I understand. Let me process that for you.`,
      type: 'text',
    })
  }

  const handleVoiceRecorded = (_blob: Blob) => {
    addUserMessage('🎤 Voice message')
    simulateAIResponse({
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: 'I received your voice message. Processing...',
      type: 'text',
    })
  }

  const handleOptionSelect = (optionId: string) => {
    addUserMessage(`Selected: ${optionId}`)
    simulateAIResponse({
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: `Got it. Moving forward with your selection.`,
      type: 'text',
    })
  }

  const handleConfirm = () => {
    addUserMessage('✓ Confirmed')
    simulateAIResponse({
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: 'Operation confirmed and executed successfully.',
      type: 'text',
    })
  }

  const handleCancel = () => {
    addUserMessage('✕ Cancelled')
    simulateAIResponse({
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: 'Operation cancelled. No changes were made.',
      type: 'text',
    })
  }

  return (
    <ConversationPage
      messages={messages}
      isTyping={isTyping}
      onSendText={handleSendText}
      onVoiceRecorded={handleVoiceRecorded}
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
