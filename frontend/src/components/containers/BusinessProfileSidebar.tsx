import { useRef } from 'react'
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
  onLogoUpload?: (dataUrl: string) => void
}

const MAX_FILE_SIZE = 20 * 1024 * 1024 // 20MB

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

export function BusinessProfileSidebar({ profile, onLogoUpload }: Props) {
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleLogoClick = () => {
    fileInputRef.current?.click()
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    if (file.size > MAX_FILE_SIZE) {
      alert('Image must be 20MB or less')
      return
    }

    if (!file.type.startsWith('image/')) {
      alert('Please select an image file')
      return
    }

    const reader = new FileReader()
    reader.onload = () => {
      const dataUrl = reader.result as string
      onLogoUpload?.(dataUrl)
    }
    reader.readAsDataURL(file)

    // Reset input so same file can be re-selected
    e.target.value = ''
  }

  return (
    <aside className="flex h-full w-72 flex-col border-r border-zinc-800/40 bg-[#0a0a0a] p-4">
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        onChange={handleFileChange}
        className="hidden"
      />

      {/* Logo Section — clickable */}
      <div className="mb-6 flex flex-col items-center">
        <button
          onClick={handleLogoClick}
          className="relative mb-3 cursor-pointer transition-opacity hover:opacity-80"
          title="Upload business logo (max 20MB)"
        >
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
        </button>
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
        <p className="text-center text-[10px] text-white/70">
          {profile.businessName ? `${import.meta.env.VITE_AGENT_NAME || 'Jay'} is here to help you setup your business profile` : `Hey! ${import.meta.env.VITE_AGENT_NAME || 'Jay'} is here, use the mic or text me when you are ready` }
        </p>
      </div>
    </aside>
  )
}
