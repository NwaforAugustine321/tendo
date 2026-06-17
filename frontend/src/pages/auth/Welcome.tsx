import { Link } from 'react-router-dom'
import { BotAvatar } from '../../components/atoms/BotAvatar'

export function Welcome() {
  return (
    <div className="flex min-h-dvh items-center justify-center bg-[#0a0a0a] px-4">
      <div className="w-full max-w-md text-center">
        <div className="mx-auto">
          <BotAvatar size={72} />
        </div>

        <h1 className="mt-6 text-2xl font-semibold tracking-tight text-white">
          Welcome to Tendo!
        </h1>
        <p className="mt-3 text-sm text-zinc-500">
          Your account is ready. Let Tendo know about your business so it can start learning how you operate.
        </p>

        <Link
          to="/onboarding"
          className="mt-8 inline-flex w-full items-center justify-center rounded-md bg-[#3ecf8e] px-4 py-2.5 text-sm font-semibold text-[#0a0a0a] transition hover:bg-[#5ee9b0]"
        >
          Tell Tendo about my business
        </Link>

        <p className="mt-6 text-xs text-zinc-600">
          Already have a login?{' '}
          <Link to="/login" className="text-[#3ecf8e] hover:underline">Sign in</Link>
        </p>
      </div>
    </div>
  )
}
