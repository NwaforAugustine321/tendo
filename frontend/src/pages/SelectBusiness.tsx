import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { getProfiles, type BusinessProfile } from '../lib/services/business'
import { Spinner } from '../components/atoms/Spinner'

export function SelectBusiness() {
  const navigate = useNavigate()
  const [profiles, setProfiles] = useState<BusinessProfile[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getProfiles().then((p) => {
      setProfiles(p)
      setLoading(false)
      if (p.length === 0) {
        navigate('/onboarding', { replace: true })
      }
    }).catch(() => {
      setLoading(false)
      navigate('/onboarding', { replace: true })
    })
  }, [navigate])

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
          Select a business
        </h1>
        <p className="mt-2 text-center text-sm text-zinc-500">
          Choose a business profile to continue.
        </p>

        <div className="mt-8 space-y-3">
          {profiles.map((p) => (
            <Link
              key={p.id}
              to="/app"
              className="flex items-center gap-3 rounded-xl border border-zinc-800/90 bg-[#141414] p-4 transition-colors hover:border-zinc-700/90 hover:bg-[#1a1a1a]"
            >
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#3ecf8e]/10 text-[#3ecf8e]">
                <span className="text-lg font-bold">{(p.name || p.email || 'B')[0].toUpperCase()}</span>
              </div>
              <div>
                <p className="text-sm font-medium text-white">{p.name || p.email || 'Untitled business'}</p>
                <p className="text-xs text-zinc-500">{p.business_id}</p>
              </div>
            </Link>
          ))}
        </div>

        <div className="mt-8 text-center">
          <Link to="/onboarding" className="text-sm text-[#3ecf8e] hover:underline">
            + Create a new business
          </Link>
        </div>
      </div>
    </div>
  )
}
