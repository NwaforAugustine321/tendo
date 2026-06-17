import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

const inputClass =
  'mt-1 w-full rounded-md border border-zinc-800/90 bg-[#090909] px-3 py-2 text-[13px] text-zinc-100 placeholder:text-zinc-600 focus:border-zinc-600 focus:outline-none focus:ring-1 focus:ring-zinc-800/50'

export const authInputClass = inputClass

export function AuthCard({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string
  subtitle?: string
  children: ReactNode
  footer?: ReactNode
}) {
  return (
    <div className="flex min-h-dvh items-center justify-center bg-[#0a0a0a] px-4">
      <div className="w-full max-w-md">
        {/* Logo + home link */}
        <div className="mb-8 flex flex-col items-center gap-3">
          <Link to="/" className="flex h-10 w-10 items-center justify-center rounded-full bg-white border-2 border-zinc-900 transition hover:scale-105">
            <span className="flex items-center gap-[3px]">
              <span className="h-[6px] w-[6px] rounded-full bg-purple-600" />
              <span className="h-[6px] w-[6px] rounded-full bg-purple-600" />
            </span>
          </Link>
          <Link to="/" className="text-xs text-zinc-600 hover:text-zinc-400 transition-colors">
            ← Back to home
          </Link>
        </div>

        <p className="font-sans text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">Account</p>
        <h1 className="mt-3 font-sans text-2xl font-semibold tracking-tight text-white">{title}</h1>
        {subtitle && <p className="mt-2 text-sm leading-relaxed text-zinc-500">{subtitle}</p>}
        <div className="mt-8 space-y-4">{children}</div>
        {footer && (
          <div className="mt-8 border-t border-zinc-800/60 pt-6 text-center text-sm text-zinc-500">{footer}</div>
        )}
      </div>
    </div>
  )
}
