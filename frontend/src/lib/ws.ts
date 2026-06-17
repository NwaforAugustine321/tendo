/**
 * WebSocket client with intelligent auto-reconnect.
 * Exponential backoff, max retries, and connection state tracking.
 */

export type WSMessage = {
  type: string
  data?: string
}

export type WSCallbacks = {
  onMessage: (msg: WSMessage) => void
  onOpen?: () => void
  onClose?: () => void
  onError?: (error: string) => void
  onReconnecting?: (attempt: number, maxAttempts: number) => void
  onReconnected?: () => void
}

type WSOptions = {
  maxRetries?: number
  baseDelay?: number
  maxDelay?: number
  autoReconnect?: boolean
}

const DEFAULT_OPTIONS: Required<WSOptions> = {
  maxRetries: 10,
  baseDelay: 1000,
  maxDelay: 30000,
  autoReconnect: true,
}

export class WSClient {
  private ws: WebSocket | null = null
  private callbacks: WSCallbacks
  private options: Required<WSOptions>
  private url: string = ''
  private retryCount = 0
  private retryTimer: ReturnType<typeof setTimeout> | null = null
  private intentionallyClosed = false

  constructor(callbacks: WSCallbacks, options?: WSOptions) {
    this.callbacks = callbacks
    this.options = { ...DEFAULT_OPTIONS, ...options }
  }

  async connect(url: string): Promise<void> {
    this.url = url
    this.intentionallyClosed = false
    this.retryCount = 0
    return this._connect()
  }

  private _connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(this.url)

      this.ws.onopen = () => {
        this.retryCount = 0
        this.callbacks.onOpen?.()
        if (this.retryCount > 0) {
          this.callbacks.onReconnected?.()
        }
        resolve()
      }

      this.ws.onmessage = (event) => {
        const msg = JSON.parse(event.data) as WSMessage
        this.callbacks.onMessage(msg)
      }

      this.ws.onerror = () => {
        if (this.retryCount === 0) {
          this.callbacks.onError?.('WebSocket connection error')
          reject(new Error('WebSocket connection failed'))
        }
      }

      this.ws.onclose = () => {
        this.callbacks.onClose?.()

        if (!this.intentionallyClosed && this.options.autoReconnect) {
          this._scheduleReconnect()
        }
      }
    })
  }

  private _scheduleReconnect() {
    if (this.retryCount >= this.options.maxRetries) {
      this.callbacks.onError?.('Connection lost. Max reconnect attempts reached.')
      return
    }

    this.retryCount++

    // Exponential backoff with jitter
    const delay = Math.min(
      this.options.baseDelay * Math.pow(2, this.retryCount - 1) + Math.random() * 500,
      this.options.maxDelay
    )

    this.callbacks.onReconnecting?.(this.retryCount, this.options.maxRetries)

    this.retryTimer = setTimeout(async () => {
      try {
        await this._connect()
        this.callbacks.onReconnected?.()
      } catch {
        // _connect failed, onclose will trigger another retry
      }
    }, delay)
  }

  send(msg: WSMessage): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(msg))
    }
  }

  isOpen(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }

  close(): void {
    this.intentionallyClosed = true
    if (this.retryTimer) {
      clearTimeout(this.retryTimer)
      this.retryTimer = null
    }
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }
}
