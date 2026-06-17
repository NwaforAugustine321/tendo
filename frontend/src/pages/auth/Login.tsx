import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { login } from '../../lib/services/auth'
import { AuthCard, authInputClass } from './AuthCard'

export function Login() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setBusy(true)

    try {
      await login(email.trim(), password)
      navigate('/app', { replace: true })
    } catch (err: any) {
      setError(err.message || 'Login failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthCard
      title="Log in"
      subtitle="Welcome back to Tendo."
      footer={
        <p>
          No account?{' '}
          <Link to="/register" className="text-[#3ecf8e] hover:underline">Register</Link>
        </p>
      }
    >
      <form className="space-y-4" onSubmit={onSubmit}>
        {error && (
          <p className="rounded-md border border-red-500/20 bg-red-950/20 px-3 py-2 text-xs text-red-400">{error}</p>
        )}
        <label className="block text-[11px] font-medium text-zinc-500">
          Email
          <input className={authInputClass} type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
        <label className="block text-[11px] font-medium text-zinc-500">
          Password
          <input className={authInputClass} type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
        </label>
        <div className="flex items-center justify-between pt-1">
          <Link to="/forgot-password" className="text-xs font-medium text-[#3ecf8e] hover:underline">
            Forgot password?
          </Link>
        </div>
        <div className="pt-2">
          <button type="submit" disabled={busy} className="w-full rounded-md bg-[#3ecf8e] px-4 py-2.5 text-sm font-semibold text-[#0a0a0a] transition hover:bg-[#5ee9b0] disabled:opacity-50">
            {busy ? 'Signing in…' : 'Sign in'}
          </button>
        </div>
      </form>
    </AuthCard>
  )
}
