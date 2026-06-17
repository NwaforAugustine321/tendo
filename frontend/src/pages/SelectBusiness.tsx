import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getProfiles, type BusinessProfile } from '../lib/services/business'
import { Spinner } from '../components/atoms/Spinner'
import { TalkingCharacter } from '../components/containers/TalkingCharacter'

export function SelectBusiness() {
  const [profiles, setProfiles] = useState<BusinessProfile[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getProfiles().then((p) => {
      setProfiles(p)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex h-dvh items-center justify-center bg-[#0a0a0a]">
        <Spinner size="lg" />
      </div>
    )
  }

  return (
    <div className="flex min-h-dvh items-center justify-center bg-[#0a0a0a] px-4">
      <div className="w-full max-w-md">
        <div className="mb-8 flex justify-center">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-white border-2 border-zinc-900">
            <span className="flex items-center gap-[3px]">
              <span className="h-[6px] w-[6px] rounded-full bg-purple-600" />
              <span className="h-[6px] w-[6px] rounded-full bg-purple-600" />
            </span>
          </div>
        </div>

        <h1 className="text-center text-2xl font-semibold tracking-tight text-white">
          Welcome!, Choose your business Profile
        </h1>
        <p className="mt-2 text-center text-sm text-zinc-500">
          Choose an existing business or create a new one.
        </p>

        {/* Existing profiles */}
        {profiles.length > 0 && (
          <div className="mt-8 space-y-3">
            {profiles.map((p) => (
              <Link
                key={p.id}
                to="/app"
                className="flex items-center gap-3 rounded-xl border border-zinc-800/90 bg-[#141414] p-4 transition-colors hover:border-zinc-700/90 hover:bg-[#1a1a1a]"
              >
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#3ecf8e]/10 text-[#3ecf8e]">
                  <span className="text-lg font-bold">{(p.name || 'B')[0].toUpperCase()}</span>
                </div>
                <div>
                  <p className="text-sm font-medium text-white">{p.name || 'Untitled business'}</p>
                  <p className="text-xs text-zinc-500">Continue with this business</p>
                </div>
              </Link>
            ))}
          </div>
        )}

        {/* Create new business */}
        <Link
          to="/onboarding"
          className="mt-6 flex items-center gap-3 rounded-xl border border-dashed border-[#3ecf8e]/40 bg-[#0a0a0a] p-4 transition-colors hover:border-[#3ecf8e]/70 hover:bg-[#141414]"
        >
          <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-[#3ecf8e]/30 text-[#3ecf8e]">
            <span className="text-xl">+</span>
          </div>
          <div>
            <p className="text-sm font-medium text-[#3ecf8e]">Create new business</p>
            <p className="text-xs text-zinc-500">Let Tendo learn about a new business</p>
          </div>
        </Link>

        {profiles.length === 0 && (
          <p className="mt-6 text-center text-xs text-zinc-600">
            You don't have any business profiles yet. Create one to get started.
          </p>
        )}
      </div>

      <TalkingCharacter isSpeaking={false} />
    </div>
  )
}
