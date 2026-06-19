/**
 * Silence Timer — monitors inactivity and fires callback after timeout.
 * Reset on any audio/text activity. Protects API tokens.
 */

const DEFAULT_TIMEOUT = Number(import.meta.env.VITE_SILENCE_TIMEOUT) || 120000

export class SilenceTimer {
  private timer: ReturnType<typeof setTimeout> | null = null
  private timeout: number
  private onTimeout: () => void

  constructor(onTimeout: () => void, timeout = DEFAULT_TIMEOUT) {
    this.onTimeout = onTimeout
    this.timeout = timeout
  }

  start() {
    this.reset()
  }

  reset() {
    if (this.timer) clearTimeout(this.timer)
    this.timer = setTimeout(() => {
      this.timer = null
      this.onTimeout()
    }, this.timeout)
  }

  stop() {
    if (this.timer) {
      clearTimeout(this.timer)
      this.timer = null
    }
  }

  isActive() {
    return this.timer !== null
  }
}
