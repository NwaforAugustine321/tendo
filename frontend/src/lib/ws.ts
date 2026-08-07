/**
 * Socket.IO client — singleton connection + reusable hook for components.
 */

import { io, type Socket } from 'socket.io-client'
import { useEffect } from 'react'

// --- Singleton socket ---

let _socket: Socket | null = null
let _refCount = 0

function getBaseUrl(): string {
  const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws/session'
  return wsUrl.replace(/^ws:\/\//, 'http://').replace(/^wss:\/\//, 'https://').replace(/\/ws\/session$/, '')
}

function getSocket(): Socket {
  if (!_socket) {
    const baseUrl = getBaseUrl()
    _socket = io(baseUrl, {
      path: '/ws/session',
      transports: ['websocket'],
      reconnection: true,
      reconnectionAttempts: Infinity,
      reconnectionDelay: 2000,
      reconnectionDelayMax: 30000,
      withCredentials: true,
    })
    _socket.on('connect', () => console.log('[ws] connected'))
    _socket.on('disconnect', (reason) => console.log('[ws] disconnected:', reason))

    // Global events dispatched as CustomEvents for legacy listeners
    _socket.on('record_processing_status', (data: any) => {
      window.dispatchEvent(new CustomEvent('tendo:record-processing', { detail: data }))
    })
    _socket.on('snapshot_updated', (data: any) => {
      window.dispatchEvent(new CustomEvent('tendo:snapshot-updated', { detail: data }))
    })
  }
  return _socket
}

export function connectSocket(): Socket {
  _refCount++
  return getSocket()
}

export function disconnectSocket(): void {
  _refCount--
  if (_refCount <= 0 && _socket) {
    _socket.disconnect()
    _socket = null
    _refCount = 0
  }
}

export function emitEvent(event: string, data: any): void {
  const socket = getSocket()
  if (socket.connected) {
    socket.emit(event, data)
  }
}

export function onEvent(event: string, handler: (data: any) => void): void {
  getSocket().on(event, handler)
}

export function offEvent(event: string, handler: (data: any) => void): void {
  getSocket().off(event, handler)
}

// --- React hook ---

export function useSocketEvent(event: string, handler: (data: any) => void, deps: any[] = []) {
  useEffect(() => {
    const socket = connectSocket()
    socket.on(event, handler)
    return () => {
      socket.off(event, handler)
      disconnectSocket()
    }
  }, deps)
}

// --- WSClient (used by ChatPanel for per-session connections) ---

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

  constructor(callbacks: WSCallbacks) {
    this.callbacks = callbacks
  }

  async connect(url: string): Promise<void> {
    const httpUrl = url.replace(/^ws:\/\//, 'http://').replace(/^wss:\/\//, 'https://')
    const urlObj = new URL(httpUrl)
    const path = urlObj.pathname
    const params = new URLSearchParams(urlObj.search)
    const query: Record<string, string> = {}
    params.forEach((v, k) => { query[k] = v })

    return new Promise((resolve, reject) => {
      this.socket = io(urlObj.origin, {
        path,
        query,
        transports: ['websocket'],
        reconnection: true,
        reconnectionAttempts: Infinity,
        reconnectionDelay: 1000,
        reconnectionDelayMax: 30000,
        timeout: 10000,
        withCredentials: true,
      })

      this.socket.on('connect', () => {
        this.callbacks.onOpen?.()
        resolve()
      })

      this.socket.on('message', (data: any) => {
        const msg = typeof data === 'string' ? JSON.parse(data) : data
        this.callbacks.onMessage(msg)
      })

      this.socket.on('disconnect', () => {
        this.callbacks.onClose?.()
      })

      this.socket.on('connect_error', (err) => {
        if (!this.socket?.connected) {
          this.callbacks.onError?.('Connecting...')
          reject(new Error(err.message))
        }
      })

      this.socket.io.on('reconnect_attempt', (attempt) => {
        this.callbacks.onReconnecting?.(attempt, Infinity)
      })

      this.socket.io.on('reconnect', () => {
        this.callbacks.onReconnected?.()
      })
    })
  }

  send(msg: WSMessage): boolean {
    if (this.socket?.connected) {
      this.socket.emit('message', msg)
      return true
    }
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
