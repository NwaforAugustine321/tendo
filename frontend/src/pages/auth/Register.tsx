import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { register } from '../../lib/services/auth'
import { AuthCard, authInputClass } from './AuthCard'

export function Register() {
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [busy, setBusy] = useState(false)

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()

    if (password !== confirm) { toast.error('Passwords do not match'); return }
    if (password.length < 8) { toast.error('Password must be at least 8 characters'); return }

    setBusy(true)
    try {
      await register(email.trim(), password, name.trim())
      toast.success('Account created!')
      navigate('/welcome', { replace: true })
    } catch {
      // Error already shown by http service toast
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
          <Link to="/login" className="text-[#3ecf8e] hover:underline">Log in</Link>
        </p>
      }
    >
      <form className="space-y-4" onSubmit={onSubmit}>
        <label className="block text-[11px] font-medium text-zinc-500">
          Name
          <input className={authInputClass} type="text" autoComplete="name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Your name" />
        </label>
        <label className="block text-[11px] font-medium text-zinc-500">
          Email
          <input className={authInputClass} type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
        <label className="block text-[11px] font-medium text-zinc-500">
          Password
          <input className={authInputClass} type="password" autoComplete="new-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
        </label>
        <label className="block text-[11px] font-medium text-zinc-500">
          Confirm password
          <input className={authInputClass} type="password" autoComplete="new-password" required value={confirm} onChange={(e) => setConfirm(e.target.value)} />
        </label>
        <div className="pt-2">
          <button type="submit" disabled={busy} className="w-full rounded-md bg-[#3ecf8e] px-4 py-2.5 text-sm font-semibold text-[#0a0a0a] transition hover:bg-[#5ee9b0] disabled:opacity-50">
            {busy ? 'Creating…' : 'Register'}
          </button>
        </div>
      </form>
    </AuthCard>
  )
}
