import { Link } from 'react-router-dom'
import { TalkingCharacter } from '../../components/containers/TalkingCharacter'

export function Welcome() {
  return (
    <div className="flex min-h-dvh flex-col items-center justify-center bg-[#0a0a0a] px-4">
      {/* Logo centered */}
      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-white border-2 border-zinc-900">
        <span className="flex items-center gap-[3px]">
          <span className="h-[6px] w-[6px] rounded-full bg-purple-600" />
          <span className="h-[6px] w-[6px] rounded-full bg-purple-600" />
        </span>
      </div>

      <h1 className="mt-6 text-2xl font-semibold tracking-tight text-white">
        Welcome to Tendo!
      </h1>
      <p className="mt-3 max-w-sm text-center text-sm text-zinc-500">
        Your account is ready. Let Tendo know about your business so it can start learning how you operate.
      </p>

      <Link
        to="/onboarding"
        className="mt-8 inline-flex items-center justify-center rounded-md bg-[#3ecf8e] px-6 py-2.5 text-sm font-semibold text-[#0a0a0a] transition hover:bg-[#5ee9b0]"
      >
        Tell Tendo about my business
      </Link>

      <p className="mt-6 text-xs text-zinc-600">
        Already have a login?{' '}
        <Link to="/login" className="text-[#3ecf8e] hover:underline">Sign in</Link>
      </p>

      {/* 3D Character */}
      <TalkingCharacter isSpeaking={false} />
    </div>
  )
}
