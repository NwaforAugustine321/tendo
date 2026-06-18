import { create } from 'zustand'
import { type BusinessProfile, getProfiles } from '../lib/services/business'

type BusinessStore = {
  profiles: BusinessProfile[]
  currentProfile: BusinessProfile | null
  loading: boolean
  fetchProfiles: () => Promise<void>
  setCurrentProfile: (profile: BusinessProfile) => void
  setCurrentProfileById: (id: string) => void
}

export const useBusinessStore = create<BusinessStore>((set, get) => ({
  profiles: [],
  currentProfile: null,
  loading: false,

  fetchProfiles: async () => {
    set({ loading: true })
    try {
      const profiles = await getProfiles()
      set({ profiles, loading: false })
      // Auto-select first profile if none selected
      if (!get().currentProfile && profiles.length > 0) {
        set({ currentProfile: profiles[0] })
      }
    } catch {
      set({ loading: false })
    }
  },

  setCurrentProfile: (profile) => {
    set({ currentProfile: profile })
  },

  setCurrentProfileById: (id) => {
    const profile = get().profiles.find((p) => p.id === id)
    if (profile) set({ currentProfile: profile })
  },
}))
