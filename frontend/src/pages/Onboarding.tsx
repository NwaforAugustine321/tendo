import { useState, useEffect } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { BusinessProfileSidebar, type BusinessProfileData } from '../components/containers'
import { TopBar } from '../components/containers'
import { getProfile } from '../lib/services/business'

export function Onboarding() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const businessId = searchParams.get('business_id') || ''

  const [profile, setProfile] = useState<BusinessProfileData>({})

  // Fetch existing profile data to prefill
  useEffect(() => {
    if (businessId) {
      getProfile(businessId).then((p) => {
        if (p) {
          setProfile({
            businessName: p.name || undefined,
            businessType: p.category || undefined,
            description: p.description || undefined,
            phone: p.phone || undefined,
            location: p.location || undefined,
            logo: p.logo_url || undefined,
            metadata: (p as any).metadata || undefined,
          })
        }
      })
    }
  }, [businessId])

  return (
    <div className="flex h-dvh flex-col overflow-hidden bg-[#0a0a0a] text-zinc-100">
      <TopBar onMenuClick={() => {}} />
      <div className="flex min-h-0 flex-1 items-start justify-center py-8">
        <div className="w-full max-w-md">
          <BusinessProfileSidebar
            profile={profile}
            businessId={businessId}
            onProfileUpdate={(data) => {
              setProfile((prev) => ({ ...prev, ...data }))
            }}
            onComplete={() => navigate('/app')}
            onLogoUpload={async (dataUrl) => {
              setProfile((prev) => ({ ...prev, logo: dataUrl }))

              try {
                const res = await fetch(dataUrl)
                const blob = await res.blob()
                const formData = new FormData()
                formData.append('file', blob, 'logo.png')

                const uploadRes = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/upload/logo?business_id=${businessId}`, {
                  method: 'POST',
                  body: formData,
                  credentials: 'include',
                })
                const data = await uploadRes.json()

                if (data.url) {
                  setProfile((prev) => ({ ...prev, logo: data.url }))
                }
              } catch (err) {
                console.error('Logo upload failed:', err)
              }
            }}
          />
        </div>
      </div>
    </div>
  )
}
