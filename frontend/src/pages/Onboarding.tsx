import { Conversation } from './Conversation'
import type { MessageItem } from '../components/conversation/ConversationPage'
import { TopBar } from '../components/dashboard/TopBar'

const ONBOARDING_MESSAGES: MessageItem[] = [
  {
    id: 'welcome-1',
    role: 'assistant',
    content:
      'Welcome. I am Tendo, your AI business assistant.\n\nI will help you manage your business by learning how you operate. You can communicate with me using voice or text.\n\nLet\'s start by getting to know your business.',
    type: 'text',
  },
  {
    id: 'welcome-2',
    role: 'assistant',
    content: 'What is the name of your business?',
    type: 'text',
  },
]

/**
 * Onboarding is the first conversation session.
 * Same page, same components — just seeded with welcome messages.
 */
export function Onboarding() {
  return (
    <div className="flex h-dvh flex-col overflow-hidden bg-[#0a0a0a] text-zinc-100">
      <TopBar onMenuClick={() => {}} />
      <div className="min-h-0 flex-1">
        <Conversation
          initialMessages={ONBOARDING_MESSAGES}
          sessionTitle="Getting to Know Your Business"
          fullScreen={false}
          showHeader={true}
        />
      </div>
    </div>
  )
}
