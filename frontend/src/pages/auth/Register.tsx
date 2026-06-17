import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { AuthCard, authInputClass } from './AuthCard'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export function Register() {
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')

    if (password !== confirm) {
      setError('Passwords do not match')
      return
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters')
      return
    }

    setBusy(true)

    try {
      const res = await fetch(`${API_URL}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ email: email.trim(), password, name: name.trim() }),
      })

      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        setError(data.detail || 'Registration failed')
        return
      }

      navigate('/onboarding', { replace: true })
    } catch {
      setError('Could not connect to server')
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthCard
      title="Create account"
      subtitle="Get started with Tendo."
      footer={
        <p>
          Already have an account?{' '}
          <Link to="/login" className="text-[#3ecf8e] hover:underline">
            Log in
          </Link>
        </p>
      }
    >
      <form className="space-y-4" onSubmit={onSubmit}>
        {error && (
          <p className="rounded-md border border-red-500/20 bg-red-950/20 px-3 py-2 text-xs text-red-400">
            {error}
          </p>
        )}
        <label className="block text-[11px] font-medium text-zinc-500">
          Name
          <input
            className={authInputClass}
            type="text"
            autoComplete="name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Your name"
          />
        </label>
        <label className="block text-[11px] font-medium text-zinc-500">
          Email
          <input
            className={authInputClass}
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </label>
        <label className="block text-[11px] font-medium text-zinc-500">
          Password
          <input
            className={authInputClass}
            type="password"
            autoComplete="new-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        <label className="block text-[11px] font-medium text-zinc-500">
          Confirm password
          <input
            className={authInputClass}
            type="password"
            autoComplete="new-password"
            required
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
          />
        </label>
        <div className="pt-2">
          <button
            type="submit"
            disabled={busy}
            className="w-full rounded-md bg-[#3ecf8e] px-4 py-2.5 text-sm font-semibold text-[#0a0a0a] transition hover:bg-[#5ee9b0] disabled:opacity-50"
          >
            {busy ? 'Creating…' : 'Register'}
          </button>
        </div>
      </form>
    </AuthCard>
  )
}
