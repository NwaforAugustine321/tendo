import { Link } from 'react-router-dom'
import { TalkingCharacter } from '../../components/containers/TalkingCharacter'

export function Welcome() {
  return (
    <div className="flex min-h-dvh flex-col items-center justify-center bg-[#0a0a0a] px-4">
      <h1 className="text-2xl font-semibold tracking-tight text-white">
        Welcome to Tendo!
      </h1>
      <p className="mt-3 max-w-sm text-center text-base text-zinc-400">
        Your account is ready. Let Tendo know about your business so it can start learning how you operate.
      </p>

      {/* Logo as the main CTA — big and clickable */}
      <Link to="/onboarding" className="mt-10 flex h-24 w-24 items-center justify-center rounded-full bg-white border-4 border-zinc-800 transition hover:scale-105 hover:border-[#3ecf8e]/50">
        <span className="flex items-center gap-[6px]">
          <span className="h-[14px] w-[14px] rounded-full bg-purple-600" />
          <span className="h-[14px] w-[14px] rounded-full bg-purple-600" />
        </span>
      </Link>
      <p className="mt-4 text-sm font-medium text-[#3ecf8e]">Tap to start</p>

      <p className="mt-8 text-xs text-zinc-600">
        Already have a login?{' '}
        <Link to="/login" className="text-[#3ecf8e] hover:underline">Sign in</Link>
      </p>

      <TalkingCharacter isSpeaking={false} />
    </div>
  )
}
