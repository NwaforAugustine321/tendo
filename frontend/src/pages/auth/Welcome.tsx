import { Link } from 'react-router-dom'

export function Welcome() {
  return (
    <div className="flex min-h-dvh items-center justify-center bg-[#0a0a0a] px-4">
      <div className="w-full max-w-md text-center">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-white border-2 border-zinc-900">
          <span className="flex items-center gap-[4px]">
            <span className="h-[8px] w-[8px] rounded-full bg-purple-600" />
            <span className="h-[8px] w-[8px] rounded-full bg-purple-600" />
          </span>
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
