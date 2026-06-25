const TOAST_DURATION_MS = 4000

export function showToast(message: string): void {
  const container = getOrCreateToastContainer()
  const toast = document.createElement('div')
  toast.className =
    'px-4 py-3 rounded-lg bg-[#1a1a1a] border border-white/10 text-zinc-200 text-sm shadow-lg ' +
    'pointer-events-auto opacity-0 transition-opacity duration-200'
  toast.setAttribute('role', 'status')
  toast.setAttribute('aria-live', 'polite')
  toast.textContent = message
  container.appendChild(toast)

  // Fade in
  requestAnimationFrame(() => {
    toast.style.opacity = '1'
  })

  setTimeout(() => {
    toast.style.opacity = '0'
    toast.addEventListener('transitionend', () => toast.remove(), { once: true })
  }, TOAST_DURATION_MS)
}

function getOrCreateToastContainer(): HTMLElement {
  const existing = document.getElementById('toast-container')
  if (existing) return existing
  const el = document.createElement('div')
  el.id = 'toast-container'
  el.className =
    'fixed bottom-6 left-1/2 -translate-x-1/2 z-[200] flex flex-col gap-2 pointer-events-none'
  document.body.appendChild(el)
  return el
}
