import { useEffect, useState } from 'react'
import { Loader2, CheckCircle2, XCircle } from 'lucide-react'
import clsx from 'clsx'

type ProcessingStatus = {
  status: string
  record_id: string
  error?: string | null
}

export function ProcessingNotification() {
  const [notifications, setNotifications] = useState<ProcessingStatus[]>([])

  useEffect(() => {
    const handleStatus = (e: Event) => {
      const detail = (e as CustomEvent).detail as ProcessingStatus
      setNotifications((prev) => {
        const existing = prev.findIndex((n) => n.record_id === detail.record_id)
        if (existing >= 0) {
          const updated = [...prev]
          updated[existing] = detail
          return updated
        }
        return [...prev, detail]
      })

      if (detail.status === 'completed' || detail.status === 'failed') {
        setTimeout(() => {
          setNotifications((prev) => prev.filter((n) => n.record_id !== detail.record_id))
        }, 4000)
      }
    }

    window.addEventListener('tendo:record-processing', handleStatus)
    return () => window.removeEventListener('tendo:record-processing', handleStatus)
  }, [])

  if (notifications.length === 0) return null

  return (
    <div className="fixed top-6 right-6 z-[150] flex flex-col gap-3">
      {notifications.map((n) => (
        <div
          key={n.record_id}
          className="flex items-center gap-3 rounded-xl px-5 py-3.5 shadow-2xl transition-all duration-300 min-w-[260px] bg-[#0a0a0a] border border-zinc-800 text-zinc-200"
        >
          {n.status === 'processing' && <Loader2 size={18} className="animate-spin text-zinc-400" />}
          {n.status === 'completed' && <CheckCircle2 size={18} className="text-zinc-400" />}
          {n.status === 'failed' && <XCircle size={18} className="text-red-400" />}
          <span className="text-sm font-medium text-white">
            {n.status === 'processing' && 'Processing...'}
            {n.status === 'completed' && 'Content processed'}
            {n.status === 'failed' && (n.error || 'Processing failed')}
          </span>
        </div>
      ))}
    </div>
  )
}
