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
    <div className="fixed top-16 right-4 z-[150] flex flex-col gap-2">
      {notifications.map((n) => (
        <div
          key={n.record_id}
          className={clsx(
            'flex items-center gap-2 rounded-lg border px-4 py-2.5 shadow-lg transition-all duration-300',
            n.status === 'processing' && 'border-[#3ecf8e]/30 bg-[#1a1a1a] text-zinc-200',
            n.status === 'completed' && 'border-green-500/30 bg-[#1a1a1a] text-green-400',
            n.status === 'failed' && 'border-red-500/30 bg-[#1a1a1a] text-red-400',
          )}
        >
          {n.status === 'processing' && <Loader2 size={14} className="animate-spin text-[#3ecf8e]" />}
          {n.status === 'completed' && <CheckCircle2 size={14} />}
          {n.status === 'failed' && <XCircle size={14} />}
          <span className="text-xs font-medium">
            {n.status === 'processing' && 'Processing record...'}
            {n.status === 'completed' && 'Record processed'}
            {n.status === 'failed' && (n.error || 'Processing failed')}
          </span>
        </div>
      ))}
    </div>
  )
}
