/**
 * WebSocket client — generic, reusable WebSocket connection management.
 * The voice-client and other features import from here.
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
}

export class WSClient {
  private ws: WebSocket | null = null
  private callbacks: WSCallbacks

  constructor(callbacks: WSCallbacks) {
    this.callbacks = callbacks
  }

  async connect(url: string): Promise<void> {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(url)

      this.ws.onopen = () => {
        this.callbacks.onOpen?.()
        resolve()
      }

      this.ws.onmessage = (event) => {
        const msg = JSON.parse(event.data) as WSMessage
        this.callbacks.onMessage(msg)
      }

      this.ws.onerror = () => {
        this.callbacks.onError?.('WebSocket connection error')
        reject(new Error('WebSocket connection failed'))
      }

      this.ws.onclose = () => {
        this.callbacks.onClose?.()
      }
    })
  }

  send(msg: WSMessage): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(msg))
    }
  }

  sendRaw(data: string): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(data)
    }
  }

  isOpen(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }

  close(): void {
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }
}
