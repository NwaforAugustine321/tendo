/**
 * Socket.IO client wrapper — drop-in replacement for the old WSClient.
 * Auto-reconnect, heartbeat, and connection state management built-in.
 */

import { io, type Socket } from 'socket.io-client'

export type WSMessage = {
  type: string
  data?: any
}

export type WSCallbacks = {
  onMessage: (msg: WSMessage) => void
  onOpen?: () => void
  onClose?: () => void
  onError?: (error: string) => void
  onReconnecting?: (attempt: number, maxAttempts: number) => void
  onReconnected?: () => void
}

export class WSClient {
  private socket: Socket | null = null
  private callbacks: WSCallbacks
  private url: string = ''

  constructor(callbacks: WSCallbacks) {
    this.callbacks = callbacks
  }

  async connect(url: string): Promise<void> {
    this.url = url

    // Convert ws:// URL to http:// for Socket.IO
    const httpUrl = url.replace(/^ws:\/\//, 'http://').replace(/^wss:\/\//, 'https://')

    // Extract path and query from URL
    const urlObj = new URL(httpUrl)
    const path = urlObj.pathname
    const query = Object.fromEntries(urlObj.searchParams.entries())

    return new Promise((resolve, reject) => {
      this.socket = io(urlObj.origin, {
        path: path,
        query: query,
        transports: ['websocket'],
        reconnection: true,
        reconnectionAttempts: Infinity,
        reconnectionDelay: 1000,
        reconnectionDelayMax: 30000,
        timeout: 120000,
        pingTimeout: 120000,
        pingInterval: 30000,
        withCredentials: true,
      })

      this.socket.on('connect', () => {
        console.log('[Socket.IO] connected')
        this.callbacks.onOpen?.()
        resolve()
      })

      this.socket.on('message', (data: any) => {
        const msg = typeof data === 'string' ? JSON.parse(data) : data
        this.callbacks.onMessage(msg)
      })

      this.socket.on('record_processing_status', (data: any) => {
        window.dispatchEvent(new CustomEvent('tendo:record-processing', { detail: data }))
      })

      this.socket.on('snapshot_updated', (data: any) => {
        window.dispatchEvent(new CustomEvent('tendo:snapshot-updated', { detail: data }))
      })

      this.socket.on('disconnect', (reason) => {
        console.log('[Socket.IO] disconnected:', reason)
        this.callbacks.onClose?.()
      })

      this.socket.on('connect_error', (err) => {
        console.warn('[Socket.IO] connect error:', err.message)
        if (!this.socket?.connected) {
          this.callbacks.onError?.('Connecting...')
          reject(new Error(err.message))
        }
      })

      this.socket.io.on('reconnect_attempt', (attempt) => {
        this.callbacks.onReconnecting?.(attempt, Infinity)
      })

      this.socket.io.on('reconnect', () => {
        console.log('[Socket.IO] reconnected')
        this.callbacks.onReconnected?.()
      })

      this.socket.io.on('reconnect_error', () => {
        // Silently handled — socket.io will keep retrying
      })
    })
  }

  send(msg: WSMessage): boolean {
    if (this.socket?.connected) {
      this.socket.emit('message', msg)
      return true
    }
    console.warn('[Socket.IO] send failed — not connected')
    return false
  }

  isOpen(): boolean {
    return this.socket?.connected ?? false
  }

  close(): void {
    if (this.socket) {
      this.socket.disconnect()
      this.socket = null
    }
  }
}
