import { createContext, useContext, useEffect, type ReactNode } from 'react'
import { useAuthStore } from '../store/auth'
import type { AuthUser } from '../lib/services/auth'

type AuthState = {
  user: AuthUser | null
  loading: boolean
  refresh: () => Promise<void>
}

const AuthContext = createContext<AuthState>({ user: null, loading: true, refresh: async () => {} })

export function AuthProvider({ children }: { children: ReactNode }) {
  const { user, loading, fetchUser } = useAuthStore()

  useEffect(() => { fetchUser() }, [])

  return (
    <AuthContext.Provider value={{ user, loading, refresh: fetchUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
