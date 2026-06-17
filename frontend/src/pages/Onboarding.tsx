import { Conversation } from './Conversation'
import { TopBar } from '../components/containers'

export function Onboarding() {
  return (
    <div className="flex h-dvh flex-col overflow-hidden bg-[#0a0a0a] text-zinc-100">
      <TopBar onMenuClick={() => {}} />
      <div className="min-h-0 flex-1">
        <Conversation
          sessionTitle="Let Tendo know about your business"
          fullScreen={false}
          showHeader={true}
        />
      </div>
    </div>
  )
}
