import { Navigate } from 'react-router-dom'
import { useAuth } from '../../context/auth'
import { Spinner } from '../atoms/Spinner'

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="flex h-dvh items-center justify-center bg-[#0a0a0a]">
        <Spinner size="lg" />
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}
