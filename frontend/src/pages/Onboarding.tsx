import { useEffect, useRef, useState } from 'react'
import { Conversation } from './Conversation'
import { TopBar } from '../components/containers'
import { startOnboarding } from '../lib/services/business'
import { Spinner } from '../components/atoms/Spinner'
import type { MessageItem } from '../components/containers'

export function Onboarding() {
  const [initialMessages, setInitialMessages] = useState<MessageItem[]>([])
  const [ready, setReady] = useState(false)
  const started = useRef(false)

  useEffect(() => {
    if (started.current) return
    started.current = true

    startOnboarding().then((message) => {
      if (message) {
        setInitialMessages([{
          id: `greeting-${Date.now()}`,
          role: 'assistant',
          content: message,
          type: 'text',
        }])
      }
      setReady(true)
    }).catch(() => setReady(true))
  }, [])

  if (!ready) {
    return (
      <div className="flex h-dvh items-center justify-center bg-[#0a0a0a]">
        <Spinner size="lg" />
      </div>
    )
  }

  return (
    <div className="flex h-dvh flex-col overflow-hidden bg-[#0a0a0a] text-zinc-100">
      <TopBar onMenuClick={() => {}} />
      <div className="min-h-0 flex-1">
        <Conversation
          initialMessages={initialMessages}
          sessionTitle="Let Tendo know about your business"
          fullScreen={false}
          showHeader={false}
        />
      </div>
    </div>
  )
}
