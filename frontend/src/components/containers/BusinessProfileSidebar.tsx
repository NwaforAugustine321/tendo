import { useRef, useState } from 'react'
import { Building2, Camera, Plus, X, Check, Pencil, Trash2, Loader2 } from 'lucide-react'
import { updateProfile, type UpdateProfileData } from '../../lib/services/business'

export type BusinessProfileData = {
  logo?: string | null
  businessName?: string
  businessType?: string
  description?: string
  phone?: string
  location?: string
  metadata?: Record<string, string>
}

type Props = {
  profile: BusinessProfileData
  businessId: string
  onLogoUpload?: (dataUrl: string) => void
  onProfileUpdate?: (data: BusinessProfileData) => void
  onComplete?: () => void
}

const MAX_FILE_SIZE = 20 * 1024 * 1024

const BUSINESS_TYPES = [
  { value: 'product', label: 'Product' },
  { value: 'service', label: 'Service' },
  { value: 'hybrid', label: 'Hybrid' },
]

function ProfileField({ label, value, placeholder, onChange, type = 'text', onFocus }: {
  label: string
  value: string
  placeholder: string
  onChange: (val: string) => void
  type?: 'text' | 'select' | 'textarea'
  onFocus?: () => void
}) {
  return (
    <div className="space-y-1">
      <label className="text-[10px] font-medium uppercase tracking-wider text-zinc-400">
        {label}
      </label>
      {type === 'select' ? (
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-full rounded-lg border border-zinc-800/40 bg-zinc-900/50 px-3 py-2 text-sm text-zinc-300 focus:border-emerald-500/50 focus:outline-none"
        >
          <option value="">Select type...</option>
          {BUSINESS_TYPES.map((t) => (
            <option key={t.value} value={t.value}>{t.label}</option>
          ))}
        </select>
      ) : type === 'textarea' ? (
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          rows={2}
          onFocus={onFocus}
          readOnly={!!onFocus}
          className={`w-full resize-none rounded-lg border border-zinc-800/40 bg-zinc-900/50 px-3 py-2 text-sm text-zinc-300 placeholder-zinc-500 focus:border-emerald-500/50 focus:outline-none ${onFocus ? 'cursor-pointer' : ''}`}
        />
      ) : (
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className="w-full rounded-lg border border-zinc-800/40 bg-zinc-900/50 px-3 py-2 text-sm text-zinc-300 placeholder-zinc-500 focus:border-emerald-500/50 focus:outline-none"
        />
      )}
    </div>
  )
}

export function BusinessProfileSidebar({ profile, businessId, onLogoUpload, onProfileUpdate, onComplete }: Props) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [form, setForm] = useState({
    businessName: profile.businessName || '',
    businessType: profile.businessType || '',
    description: profile.description || '',
    phone: profile.phone || '',
    location: profile.location || '',
  })
  const [metadata, setMetadata] = useState<Record<string, string>>(profile.metadata || {})
  const [saving, setSaving] = useState(false)
  const [showMetaModal, setShowMetaModal] = useState(false)
  const [editingKey, setEditingKey] = useState<string | null>(null)
  const [newMetaKey, setNewMetaKey] = useState('')
  const [newMetaValue, setNewMetaValue] = useState('')
  const [showDescModal, setShowDescModal] = useState(false)
  const [metaSaving, setMetaSaving] = useState(false)
  const [deletingKey, setDeletingKey] = useState<string | null>(null)

  // Sync from parent when agent updates
  const prevProfile = useRef(profile)
  if (profile !== prevProfile.current) {
    prevProfile.current = profile
    setForm({
      businessName: profile.businessName || form.businessName,
      businessType: profile.businessType || form.businessType,
      description: profile.description || form.description,
      phone: profile.phone || form.phone,
      location: profile.location || form.location,
    })
    if (profile.metadata) {
      setMetadata((prev) => ({ ...prev, ...profile.metadata }))
    }
  }

  const canComplete = !!(form.businessName.trim() && form.businessType.trim())

  const handleSave = async () => {
    setSaving(true)
    const data: UpdateProfileData = {
      name: form.businessName,
      category: form.businessType,
      description: form.description,
      phone: form.phone,
      location: form.location,
      metadata,
      onboarding_completed: true,
    }
    await updateProfile(businessId, data)
    onProfileUpdate?.({ ...form, metadata })
    setSaving(false)
    onComplete?.()
  }

  const handleAddMeta = async () => {
    if (newMetaKey.trim() && newMetaValue.trim()) {
      setMetaSaving(true)
      let updatedMetadata: Record<string, string>
      if (editingKey && editingKey !== newMetaKey.trim()) {
        updatedMetadata = { ...metadata }
        delete updatedMetadata[editingKey]
        updatedMetadata[newMetaKey.trim()] = newMetaValue.trim()
      } else {
        updatedMetadata = { ...metadata, [newMetaKey.trim()]: newMetaValue.trim() }
      }
      await updateProfile(businessId, { metadata: updatedMetadata })
      setMetadata(updatedMetadata)
      setNewMetaKey('')
      setNewMetaValue('')
      setEditingKey(null)
      setMetaSaving(false)
      setShowMetaModal(false)
    }
  }

  const handleRemoveMeta = async (key: string) => {
    setDeletingKey(key)
    const updatedMetadata = { ...metadata }
    delete updatedMetadata[key]
    await updateProfile(businessId, { metadata: updatedMetadata })
    setMetadata(updatedMetadata)
    setDeletingKey(null)
  }

  const handleLogoClick = () => fileInputRef.current?.click()

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (file.size > MAX_FILE_SIZE) return
    if (!file.type.startsWith('image/')) return

    const reader = new FileReader()
    reader.onload = () => onLogoUpload?.(reader.result as string)
    reader.readAsDataURL(file)
    e.target.value = ''
  }

  return (
    <div className="flex h-full w-full flex-col rounded-xl border border-zinc-800/40 bg-[#0a0a0a] p-5">
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        onChange={handleFileChange}
        className="hidden"
      />

      {/* Logo */}
      <div className="mb-5 flex flex-col items-center">
        <button
          onClick={handleLogoClick}
          className="relative mb-2 cursor-pointer transition-opacity hover:opacity-80"
          title="Upload logo"
        >
          {profile.logo ? (
            <img src={profile.logo} alt="Logo" className="h-16 w-16 rounded-full border-2 border-zinc-700/40 object-cover" />
          ) : (
            <div className="flex h-16 w-16 items-center justify-center rounded-full border-2 border-dashed border-zinc-700/40 bg-zinc-900">
              <Building2 size={24} className="text-zinc-400" />
            </div>
          )}
          <div className="absolute -bottom-1 -right-1 flex h-5 w-5 items-center justify-center rounded-full border border-zinc-700/40 bg-zinc-800">
            <Camera size={10} className="text-zinc-400" />
          </div>
        </button>
        <h3 className="text-sm font-semibold text-zinc-200">
          {form.businessName || 'Your Business'}
        </h3>
      </div>

      {/* Editable Fields */}
      <div className="flex-1 space-y-2.5 overflow-y-auto">
        <ProfileField label="Business Name" value={form.businessName} placeholder="e.g. Business" onChange={(v) => { setForm((f) => ({ ...f, businessName: v })); onProfileUpdate?.({ ...form, businessName: v }) }} />
        <ProfileField label="Business Type" value={form.businessType} placeholder="" onChange={(v) => { setForm((f) => ({ ...f, businessType: v })); onProfileUpdate?.({ ...form, businessType: v }) }} type="select" />
        <ProfileField label="Description" value={form.description} placeholder="What does your business do?" onChange={(v) => { setForm((f) => ({ ...f, description: v })); onProfileUpdate?.({ ...form, description: v }) }} type="textarea" onFocus={() => setShowDescModal(true)} />

        {/* Metadata display */}
        {Object.keys(metadata).length > 0 && (
          <div className="space-y-1 pt-1">
            <label className="text-[10px] font-medium uppercase tracking-wider text-zinc-400">Additional Info</label>
            {Object.entries(metadata).map(([key, value]) => (
              <div key={key} className="flex items-center gap-1 rounded border border-zinc-800/30 bg-zinc-900/30 px-2 py-1">
                <span className="text-[11px] text-zinc-400">{key}:</span>
                <span className="flex-1 truncate text-[11px] text-zinc-300">{value}</span>
                <button
                  onClick={() => {
                    setEditingKey(key)
                    setNewMetaKey(key)
                    setNewMetaValue(value)
                    setShowMetaModal(true)
                  }}
                  className="shrink-0 text-zinc-400 hover:text-orange-400"
                  title="Edit"
                >
                  <Pencil size={13} />
                </button>
                <button
                  onClick={() => handleRemoveMeta(key)}
                  disabled={deletingKey === key}
                  className="shrink-0 text-zinc-400 hover:text-red-400 disabled:opacity-50"
                  title="Remove"
                >
                  {deletingKey === key ? <Loader2 size={13} className="animate-spin" /> : <Trash2 size={13} />}
                </button>
              </div>
            ))}
          </div>
        )}

        {/* More Information button — moved to action area */}
      </div>

      {/* Action Buttons */}
      <div className="mt-3 space-y-2">
        <button
          onClick={() => {
            setNewMetaKey('')
            setNewMetaValue('')
            setEditingKey(null)
            setShowMetaModal(true)
          }}
          className="flex w-full items-center justify-center gap-1.5 rounded-lg border border-dashed border-[#3ecf8e]/40 py-2 text-[11px] text-[#3ecf8e] transition-colors hover:border-[#3ecf8e]/70 hover:text-white"
        >
          <Plus size={12} /> More Information
        </button>

        <button
          onClick={handleSave}
          disabled={saving || !form.businessName.trim()}
          className="flex w-full items-center justify-center gap-1.5 rounded-lg bg-emerald-600 py-2 text-[12px] font-medium text-white transition-colors hover:bg-emerald-500 disabled:opacity-50"
        >
          <Check size={13} />
          {saving ? 'Setting up...' : 'Setup Profile'}
        </button>
      </div>

      {/* Metadata Modal */}
      {showMetaModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="w-full max-w-lg rounded-xl border border-zinc-600/50 bg-[#1e1e1e] p-5 shadow-2xl">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-white">{editingKey ? 'Edit Information' : 'Add Information'}</h3>
              <button onClick={() => setShowMetaModal(false)} className="text-zinc-400 hover:text-white">
                <X size={16} />
              </button>
            </div>

            {/* Add new field */}
            <div className="space-y-2">
              <input
                value={newMetaKey}
                onChange={(e) => setNewMetaKey(e.target.value)}
                placeholder="Label (e.g. Opening Hours)"
                className="w-full rounded border border-zinc-700/40 bg-zinc-800/50 px-2.5 py-1.5 text-[12px] text-zinc-200 placeholder-zinc-500 focus:border-[#3ecf8e]/50 focus:outline-none"
              />
              <textarea
                value={newMetaValue}
                onChange={(e) => setNewMetaValue(e.target.value)}
                placeholder="Value (e.g. Mon-Fri 9am - 5pm, Sat 10am - 2pm)"
                rows={4}
                className="w-full resize-none rounded border border-zinc-700/40 bg-zinc-800/50 px-2.5 py-1.5 text-[12px] text-zinc-200 placeholder-zinc-500 focus:border-[#3ecf8e]/50 focus:outline-none"
              />
            </div>

            <div className="mt-4 flex items-center justify-end gap-2">
              <button
                onClick={() => setShowMetaModal(false)}
                className="rounded-lg bg-zinc-800 px-4 py-2 text-[12px] font-medium text-zinc-300 hover:bg-zinc-700"
              >
                Cancel
              </button>
              <button
                onClick={handleAddMeta}
                disabled={!newMetaKey.trim() || !newMetaValue.trim() || metaSaving}
                className="rounded-lg bg-[#3ecf8e] px-4 py-2 text-[12px] font-medium text-black transition-colors hover:bg-[#34b87a] disabled:opacity-40"
              >
                {metaSaving ? <Loader2 size={14} className="animate-spin" /> : editingKey ? 'Update' : 'Add'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Description Modal */}
      {showDescModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="w-full max-w-lg rounded-xl border border-zinc-600/50 bg-[#1e1e1e] p-5 shadow-2xl">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-white">Business Description</h3>
              <button onClick={() => setShowDescModal(false)} className="text-zinc-400 hover:text-white">
                <X size={16} />
              </button>
            </div>
            <textarea
              value={form.description}
              onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
              placeholder="Describe what your business does, what you sell or the services you provide..."
              rows={8}
              autoFocus
              className="w-full resize-none rounded-lg border border-zinc-700/40 bg-zinc-800/50 px-3 py-2.5 text-sm text-zinc-200 placeholder-zinc-500 focus:border-emerald-500/50 focus:outline-none"
            />
            <div className="mt-3 flex justify-end">
              <button
                onClick={() => { setShowDescModal(false); onProfileUpdate?.({ ...form }) }}
                className="rounded-lg bg-emerald-600 px-4 py-2 text-[12px] font-medium text-white hover:bg-emerald-500"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
