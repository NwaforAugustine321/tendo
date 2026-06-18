import { Building2, Camera } from 'lucide-react'

export type BusinessProfileData = {
  logo?: string | null
  businessName?: string
  businessType?: string
  description?: string
  phone?: string
  location?: string
}

type Props = {
  profile: BusinessProfileData
}

function ProfileField({ label, value, placeholder }: { label: string; value?: string; placeholder: string }) {
  return (
    <div className="space-y-1">
      <label className="text-[10px] font-medium uppercase tracking-wider text-zinc-500">
        {label}
      </label>
      <input
        type="text"
        value={value || ''}
        placeholder={placeholder}
        disabled
        className="w-full rounded-lg border border-zinc-800/40 bg-zinc-900/50 px-3 py-2 text-sm text-zinc-300 placeholder-zinc-700 disabled:cursor-default disabled:opacity-70"
      />
    </div>
  )
}

export function BusinessProfileSidebar({ profile }: Props) {
  return (
    <aside className="flex h-full w-72 flex-col border-r border-zinc-800/40 bg-[#0a0a0a] p-4">
      {/* Logo Section */}
      <div className="mb-6 flex flex-col items-center">
        <div className="relative mb-3">
          {profile.logo ? (
            <img
              src={profile.logo}
              alt="Business logo"
              className="h-20 w-20 rounded-full border-2 border-zinc-700/40 object-cover"
            />
          ) : (
            <div className="flex h-20 w-20 items-center justify-center rounded-full border-2 border-dashed border-zinc-700/40 bg-zinc-900">
              <Building2 size={28} className="text-zinc-600" />
            </div>
          )}
          <div className="absolute -bottom-1 -right-1 flex h-6 w-6 items-center justify-center rounded-full border border-zinc-700/40 bg-zinc-800">
            <Camera size={12} className="text-zinc-400" />
          </div>
        </div>
        <h3 className="text-sm font-semibold text-zinc-200">
          {profile.businessName || 'Your Business'}
        </h3>
        <p className="text-[11px] text-zinc-500">
          {profile.businessType || 'Setting up...'}
        </p>
      </div>

      {/* Profile Fields */}
      <div className="flex-1 space-y-3 overflow-y-auto">
        <ProfileField
          label="Business Name"
          value={profile.businessName}
          placeholder="Waiting for info..."
        />
        <ProfileField
          label="Business Type"
          value={profile.businessType}
          placeholder="Waiting for info..."
        />
        <ProfileField
          label="Description"
          value={profile.description}
          placeholder="Waiting for info..."
        />
        <ProfileField
          label="Phone"
          value={profile.phone}
          placeholder="Waiting for info..."
        />
        <ProfileField
          label="Location"
          value={profile.location}
          placeholder="Waiting for info..."
        />
      </div>

      {/* Status */}
      <div className="mt-4 rounded-lg border border-zinc-800/40 bg-zinc-900/50 px-3 py-2">
        <p className="text-center text-[10px] text-zinc-500">
          {profile.businessName ? '✓ Profile updating live' : 'Waiting for onboarding...'}
        </p>
      </div>
    </aside>
  )
}
