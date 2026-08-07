import { create } from 'zustand'
import { getMe, type AuthUser } from '../lib/services/auth'

type AuthStore = {
  user: AuthUser | null
  loading: boolean
  fetchUser: () => Promise<void>
  setUser: (user: AuthUser | null) => void
  clear: () => void
}

export const useAuthStore = create<AuthStore>((set) => ({
  user: null,
  loading: true,

  fetchUser: async () => {
    set({ loading: true })
    try {
      const user = await getMe()
      set({ user, loading: false })
    } catch {
      set({ user: null, loading: false })
    }
  },

  setUser: (user) => set({ user, loading: false }),

  clear: () => set({ user: null, loading: false }),
}))
