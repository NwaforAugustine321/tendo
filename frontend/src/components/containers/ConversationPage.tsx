import { useRef, useEffect } from 'react'
import {
  MessageBubble,
  UnderstandingCard,
  InputCard,
  ConfirmationCard,
  OperationCard,
  TypingIndicator,
  TextInput,
  VoiceButton,
  EmptyState,
} from '../atoms'
import { TalkingCharacter } from './TalkingCharacter'

export type InputSpec = {
  fields: Array<{
    id?: string
    name: string
    label?: string
    placeholder?: string
    description?: string
  }>
}

export type MessageItem = {
  id: string
  role: 'user' | 'assistant'
  content: string
  type: 'text' | 'understanding' | 'options' | 'confirmation' | 'operation' | 'input'
  audioUrl?: string
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
  inputSpec?: InputSpec
}

type Props = {
  messages: MessageItem[]
  isTyping: boolean
  thinkingText?: string
  thoughtText?: string
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
  fullScreen?: boolean
  transparentBg?: boolean
  flipCharacter?: boolean
  characterRightOffset?: number
  onWakeToggle?: () => void
  wakeActive?: boolean
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
  thinkingText,
  thoughtText,
  transparentBg = false,
  flipCharacter = false,
  characterRightOffset = 0,
  onWakeToggle,
  wakeActive = false,
}: Props) {
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: 'smooth',
      })
    }
  }, [messages, isTyping, thinkingText, thoughtText])

  return (
    <div className={`relative flex flex-col overflow-hidden bg-[#0a0a0a] ${fullScreen ? 'h-dvh' : 'h-full'}`}>
      {/* {showHeader && (
        <header className="relative z-10 flex flex-col items-center pt-4 pb-2 mb-4">
          <h1 className="text-lg font-bold tracking-[-0.03em] text-white">{headerTitle}</h1>
          <p className="mt-0.5 text-xs text-zinc-400">{headerSubtitle}</p>
        </header>
      )} */}

      <div
        ref={scrollRef}
        className="relative z-10 flex-1 overflow-y-auto px-3 pt-4 pb-4 sm:px-5"
      >
        {messages.length === 0 && !isTyping ? (
          <EmptyState />
        ) : (
          <div className="mx-auto max-w-2xl space-y-4">
            {messages.map((msg, idx) => {
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
              if (msg.type === 'input' && msg.inputSpec) {
                const isLast = idx === messages.length - 1
                return (
                  <InputCard
                    key={msg.id}
                    fields={msg.inputSpec.fields as any[] || []}
                    onSubmit={isLast ? onSendText : () => {}}
                    disabled={!isLast}
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
                  audioUrl={msg.audioUrl}
                />
              )
            })}
            {isTyping && <TypingIndicator text={thinkingText} thoughtText={thoughtText} />}
          </div>
        )}
      </div>

      <div className={`relative z-10 border-t border-zinc-800/40 ${transparentBg ? 'bg-transparent' : 'bg-[#0a0a0a]'} px-3 py-3 sm:px-5`}>
        <div className="mx-auto max-w-2xl">
          
          <div className="mb-2 flex items-center gap-2">
            <VoiceButton
              onRecorded={onVoiceRecorded}
              onToggle={onVoiceToggle}
              isListening={isListening}
            />
            <TextInput onSend={onSendText} />
          </div>
          {onWakeToggle && (
            <div className="flex justify-center">
              <button
                type="button"
                onClick={onWakeToggle}
                className={`rounded-full cursor-pointer px-3 py-1 text-[10px] font-medium transition-all ${
                  wakeActive
                    ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                    : 'bg-orange-500/10 text-orange-400 border border-orange-500/30 hover:bg-orange-500/20'
                }`}
              >
                {wakeActive
                  ? `Hey! ${import.meta.env.VITE_AGENT_NAME || 'Jay'} is here, use the mic or text me`
                  : `Hey! ${import.meta.env.VITE_AGENT_NAME || 'Jay'} is relaxing, use the mic or touch me`
                }
              </button>
            </div>
          )}
        </div>
      </div>

      {fullScreen && <TalkingCharacter isSpeaking={isTyping} flipX={flipCharacter} rightOffset={characterRightOffset} />}
    </div>
  )
}
