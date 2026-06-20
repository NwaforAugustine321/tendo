import { useState, useEffect, useRef } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { ConversationPage, type MessageItem, BusinessProfileSidebar, type BusinessProfileData } from '../components/containers'
import type { InputSpec } from '../components/containers/ConversationPage'
import { TopBar } from '../components/containers'
import { useVoiceSession } from '../hooks/useVoiceSession'
import { getProfile } from '../lib/services/business'

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
              <span className={`text-[10px] ${isActive ? 'text-orange-400' : 'text-zinc-400'}`}>
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
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const sessionId = searchParams.get('session_id') || ''
  const businessId = searchParams.get('business_id') || ''

  const [messages, setMessages] = useState<MessageItem[]>([])
  const [thinking, setThinking] = useState(false)
  const [profile, setProfile] = useState<BusinessProfileData>({})
  const [wakeActive, setWakeActive] = useState(false)

  // Derive step from profile state (works for both agent and manual fills)
  const derivedStep = (() => {
    if (!profile.businessName) return 0
    if (!profile.businessType) return 1
    if (!profile.description) return 2
    if (!profile.phone) return 3
    if (!profile.location) return 4
    return 5
  })()
  const [currentStep, setCurrentStep] = useState(derivedStep)
  const voice = useVoiceSession()
  const connected = useRef(false)
  const lastMsgId = useRef('')

  useEffect(() => {
    if (!connected.current) {
      connected.current = true
      voice.connect({ sessionId, businessId })
      // Request mic permission immediately
      navigator.mediaDevices.getUserMedia({ audio: true }).catch(() => {})
    }
  }, [])

  // Track wake state from voice connection
  useEffect(() => {
    if (voice.isConnected) setWakeActive(true)
    else setWakeActive(false)
  }, [voice.isConnected])

  // Fetch existing profile data to prefill the sidebar
  useEffect(() => {
    if (businessId) {
      getProfile(businessId).then((p) => {
        if (p) {
          setProfile({
            businessName: p.name || undefined,
            businessType: p.category || undefined,
            description: p.description || undefined,
            phone: p.phone || undefined,
            location: p.location || undefined,
            logo: p.logo_url || undefined,
            metadata: (p as any).metadata || undefined,
          })
        }
      })
    }
  }, [businessId])

  // Update progress bar when profile changes (manual or agent)
  useEffect(() => {
    if (!profile.businessName) { setCurrentStep(0); return }
    if (!profile.businessType) { setCurrentStep(1); return }
    if (!profile.description) { setCurrentStep(2); return }
    if (!profile.phone) { setCurrentStep(3); return }
    if (!profile.location) { setCurrentStep(4); return }
    setCurrentStep(5)
  }, [profile])

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
      if (!voice.isConnected) {
        await voice.connect({ sessionId, businessId })
      }
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
            businessId={businessId}
            onProfileUpdate={(data) => {
              setProfile((prev) => ({ ...prev, ...data }))
            }}
            onComplete={() => navigate('/app')}
            onLogoUpload={async (dataUrl) => {
              setProfile((prev) => ({ ...prev, logo: dataUrl }))

              try {
                const res = await fetch(dataUrl)
                const blob = await res.blob()
                const formData = new FormData()
                formData.append('file', blob, 'logo.png')

                const uploadRes = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/upload/logo?business_id=${businessId}`, {
                  method: 'POST',
                  body: formData,
                  credentials: 'include',
                })
                const data = await uploadRes.json()

                if (data.url) {
                  setProfile((prev) => ({ ...prev, logo: data.url }))
                }
              } catch (err) {
                console.error('Logo upload failed:', err)
              }
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
              thinkingText={thinking ? (voice.thinkingText || ``) : undefined}
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
              wakeActive={wakeActive}
              onWakeToggle={async () => {
                if (wakeActive) {
                  await voice.stopListening()
                  voice.disconnect()
                  setWakeActive(false)
                } else {
                  await voice.connect({ sessionId, businessId })
                  await voice.startListening()
                  setWakeActive(true)
                }
              }}
            />
          </div>
        </div>
      </div>
    </div>
  )
}
