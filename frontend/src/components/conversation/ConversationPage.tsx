import { useRef, useEffect } from 'react'
import { MessageBubble } from './MessageBubble'
import { UnderstandingCard } from './UnderstandingCard'
import { OptionCard } from './OptionCard'
import { ConfirmationCard } from './ConfirmationCard'
import { OperationCard } from './OperationCard'
import { TypingIndicator } from './TypingIndicator'
import { TextInput } from './TextInput'
import { VoiceButton } from './VoiceButton'
import { TalkingCharacter } from './TalkingCharacter'
import { EmptyState } from './EmptyState'

export type MessageItem = {
  id: string
  role: 'user' | 'assistant'
  content: string
  type: 'text' | 'understanding' | 'options' | 'confirmation' | 'operation'
  understanding?: {
    title?: string
    businessName?: string
    activities?: string[]
    behaviors?: string[]
    note?: string
  }
  options?: {
    prompt: string
    choices: { id: string; label: string; recommended?: boolean }[]
  }
  confirmation?: {
    summary: string
    details: { label: string; value: string }[]
  }
  operation?: {
    operationType: string
    changes: { label: string; before: string; after: string }[]
  }
}

type Props = {
  messages: MessageItem[]
  isTyping: boolean
  onSendText: (text: string) => void
  onVoiceRecorded: (blob: Blob) => void
  onVoiceToggle?: () => void
  isListening?: boolean
  onOptionSelect: (optionId: string) => void
  onConfirm?: () => void
  onModify?: () => void
  onCancel?: () => void
  onRevert?: (messageId: string) => void
  onContinueFromHere?: (messageId: string) => void
  showHeader?: boolean
  headerTitle?: string
  headerSubtitle?: string
  /** When true, uses h-dvh for full-screen mode (onboarding). When false, fills parent container. */
  fullScreen?: boolean
}

export function ConversationPage({
  messages,
  isTyping,
  onSendText,
  onVoiceRecorded,
  onVoiceToggle,
  isListening = false,
  onOptionSelect,
  onConfirm,
  onModify,
  onCancel,
  onRevert,
  onContinueFromHere,
  showHeader = true,
  headerTitle = 'Tendo',
  headerSubtitle = 'Your AI Business Assistant',
  fullScreen = true,
}: Props) {
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: 'smooth',
      })
    }
  }, [messages, isTyping])

  return (
    <div className={`relative flex flex-col overflow-hidden bg-[#0a0a0a] ${fullScreen ? 'h-dvh' : 'h-full'}`}>
      {/* Header */}
      {showHeader && (
        <header className="relative z-10 flex flex-col items-center pt-4 pb-2">
          <h1 className="text-lg font-bold tracking-[-0.03em] text-white">{headerTitle}</h1>
          <p className="mt-0.5 text-xs text-zinc-500">{headerSubtitle}</p>
        </header>
      )}

      {/* Messages */}
      <div
        ref={scrollRef}
        className="relative z-10 flex-1 overflow-y-auto px-3 pb-4 sm:px-5"
      >
        {messages.length === 0 && !isTyping ? (
          <EmptyState />
        ) : (
          <div className="mx-auto max-w-lg space-y-4">
            {messages.map((msg) => {
              if (msg.type === 'understanding' && msg.understanding) {
                return (
                  <UnderstandingCard
                    key={msg.id}
                    title={msg.understanding.title}
                    businessName={msg.understanding.businessName}
                    activities={msg.understanding.activities}
                    behaviors={msg.understanding.behaviors}
                    note={msg.understanding.note}
                  />
                )
              }
              if (msg.type === 'options' && msg.options) {
                return (
                  <OptionCard
                    key={msg.id}
                    prompt={msg.options.prompt}
                    choices={msg.options.choices}
                    onSelect={onOptionSelect}
                  />
                )
              }
              if (msg.type === 'confirmation' && msg.confirmation) {
                return (
                  <ConfirmationCard
                    key={msg.id}
                    summary={msg.confirmation.summary}
                    details={msg.confirmation.details}
                    onConfirm={onConfirm ?? (() => {})}
                    onModify={onModify ?? (() => {})}
                    onCancel={onCancel ?? (() => {})}
                  />
                )
              }
              if (msg.type === 'operation' && msg.operation) {
                return (
                  <OperationCard
                    key={msg.id}
                    operationType={msg.operation.operationType}
                    changes={msg.operation.changes}
                    onRevert={onRevert ? () => onRevert(msg.id) : undefined}
                    onContinueFromHere={onContinueFromHere ? () => onContinueFromHere(msg.id) : undefined}
                  />
                )
              }
              return (
                <MessageBubble
                  key={msg.id}
                  role={msg.role}
                  content={msg.content}
                />
              )
            })}
            {isTyping && <TypingIndicator />}
          </div>
        )}
      </div>

      {/* Input area */}
      <div className="relative z-10 border-t border-zinc-800/90 bg-[#0a0a0a] px-3 py-3 sm:px-5">
        <div className="mx-auto flex max-w-lg items-center gap-3">
          <VoiceButton
            onRecorded={onVoiceRecorded}
            onToggle={onVoiceToggle}
            isListening={isListening}
          />
          <TextInput onSend={onSendText} />
        </div>
      </div>

      {/* Talking character — fixed bottom-right, animates when Gemini audio plays */}
      <TalkingCharacter isSpeaking={isTyping} />
    </div>
  )
}
