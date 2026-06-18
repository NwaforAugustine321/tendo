import { useState, useEffect, useRef } from 'react'
import { ConversationPage, type MessageItem, BusinessProfileSidebar, type BusinessProfileData } from '../components/containers'
import type { InputSpec } from '../components/containers/ConversationPage'
import { TopBar } from '../components/containers'
import { useVoiceSession } from '../hooks/useVoiceSession'

const STEPS = [
  { label: 'Business Name' },
  { label: 'Business Type' },
  { label: 'Description' },
  { label: 'Phone' },
  { label: 'Location' },
  { label: 'Confirm' },
]

function StepProgress({ currentStep }: { currentStep: number }) {
  // Only show steps that are not yet completed (current + remaining)
  const remainingSteps = STEPS.filter((_, idx) => idx >= currentStep)

  return (
    <div className="flex items-center justify-center gap-3 py-2">
      {remainingSteps.map((step, displayIdx) => {
        const isActive = displayIdx === 0
        return (
          <div key={step.label} className="flex items-center gap-3">
            <div className="flex items-center gap-1.5">
              <div
                className={`flex h-5 w-5 items-center justify-center rounded-full border transition-all ${
                  isActive
                    ? 'border-orange-500 bg-orange-500/10'
                    : 'border-zinc-700 bg-zinc-900'
                }`}
              >
                <span className={`h-1.5 w-1.5 rounded-full ${isActive ? 'bg-orange-500' : 'bg-zinc-600'}`} />
              </div>
              <span className={`text-[10px] ${isActive ? 'text-orange-400' : 'text-zinc-600'}`}>
                {step.label}
              </span>
            </div>
            {displayIdx < remainingSteps.length - 1 && (
              <div className="h-px w-4 bg-zinc-700" />
            )}
          </div>
        )
      })}
    </div>
  )
}

export function Onboarding() {
  const [messages, setMessages] = useState<MessageItem[]>([])
  const [thinking, setThinking] = useState(true)
  const [currentStep, setCurrentStep] = useState(0)
  const [profile, setProfile] = useState<BusinessProfileData>({})
  const voice = useVoiceSession()
  const connected = useRef(false)
  const lastMsgId = useRef('')

  useEffect(() => {
    if (!connected.current) {
      connected.current = true
      voice.connect()
    }
  }, [])

  useEffect(() => {
    if (!voice.lastMessage) return
    if (voice.lastMessage.id === lastMsgId.current) return
    lastMsgId.current = voice.lastMessage.id
    setThinking(false)

    const { response, msgType, questions } = voice.lastMessage

    if (response) {
      setMessages((prev) => [...prev, {
        id: `text-${voice.lastMessage!.id}`,
        role: 'assistant',
        content: response,
        type: 'text',
      }])
    }

    // Update profile from agent's extracted values
    const extracted = voice.lastMessage.extracted
    if (extracted) {
      setProfile((prev) => ({
        ...prev,
        ...(extracted.business_name && { businessName: extracted.business_name }),
        ...(extracted.business_type && { businessType: extracted.business_type }),
        ...(extracted.description && { description: extracted.description }),
        ...(extracted.phone_number && { phone: extracted.phone_number }),
        ...(extracted.location && { location: extracted.location }),
      }))
    }

    if (msgType === 'question' && questions) {
      setMessages((prev) => [...prev, {
        id: `input-${voice.lastMessage!.id}`,
        role: 'assistant',
        content: '',
        type: 'input',
        inputSpec: questions as InputSpec,
      }])

      // Detect step from field name
      const fields = questions.fields || []
      if (fields.length > 0) {
        const field = fields[0]
        if (field.type === 'text' && field.name === 'business_name') setCurrentStep(0)
        else if (field.type === 'radio' && field.options?.[0]?.name === 'business_type') setCurrentStep(1)
        else if (field.type === 'text' && field.name === 'description') setCurrentStep(2)
        else if (field.type === 'text' && field.name === 'phone_number') setCurrentStep(3)
        else if (field.type === 'text' && field.name === 'location') setCurrentStep(4)
        else if (field.type === 'radio' && field.options?.[0]?.name === 'confirm') setCurrentStep(5)
      }
    }

    if (msgType === 'answer') {
      setCurrentStep(6)
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
      await voice.startListening()
    }
  }

  const findOptionContext = (optionId: string) => {
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
    <div className="flex h-dvh flex-col overflow-hidden bg-[#0a0a0a] text-zinc-100">
      <TopBar onMenuClick={() => {}} />
      <div className="flex min-h-0 flex-1">
        {/* Sidebar — below top nav, left side */}
        <div className="hidden lg:block">
          <BusinessProfileSidebar
            profile={profile}
            onLogoUpload={(dataUrl) => {
              setProfile((prev) => ({ ...prev, logo: dataUrl }))
              // Send to agent using same format as question responses (label + answer + description)
              const sendText = 'label: Business Logo, answer: [LOGO_UPLOADED], description: User uploaded a business profile image'
              setMessages((prev) => [...prev, { id: `user-${Date.now()}`, role: 'user', content: '📷 Logo uploaded', type: 'text' }])
              setThinking(true)
              voice.sendText(sendText)
            }}
          />
        </div>

        {/* Main content — step progress + chat */}
        <div className="flex flex-1 flex-col overflow-hidden">
          <div className="mx-auto w-full max-w-lg px-3 sm:px-5">
            <StepProgress currentStep={currentStep} />
          </div>
          <div className="min-h-0 flex-1">
            <ConversationPage
              messages={messages}
              isTyping={thinking || voice.isSpeaking}
              thinkingText={thinking ? `${import.meta.env.VITE_AGENT_NAME || 'Jay'} is processing your request` : undefined}
              onSendText={handleSendText}
              onVoiceRecorded={() => {}}
              onVoiceToggle={handleVoiceToggle}
              isListening={voice.isListening}
              onOptionSelect={(id) => handleSendText(id)}
              onConfirm={() => handleSendText('confirm')}
              onModify={() => {}}
              onCancel={() => handleSendText('cancel')}
              onRevert={() => {}}
              onContinueFromHere={() => {}}
              showHeader={false}
              headerSubtitle="Let Jay know about your business"
              fullScreen={false}
              transparentBg
            />
          </div>
        </div>
      </div>
    </div>
  )
}
