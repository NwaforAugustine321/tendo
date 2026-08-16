import { io, type Socket } from "socket.io-client";
import { useEffect } from "react";

const SOCKET_HEARTBEAT_INTERVAL = 30_000;

export type SocketPayload = Record<string, any>;

export type WSMessage = {
  type: string;
  payload?: SocketPayload;
};

export type WSCallbacks = {
  onMessage: (msg: WSMessage) => void;
  onOpen?: () => void;
  onClose?: () => void;
  onError?: (error: string) => void;
  onReconnecting?: (attempt: number, maxAttempts: number) => void;
  onReconnected?: () => void;
};

class SocketHeartbeat {
  private socket: Socket | null = null;
  private timer: ReturnType<typeof setInterval> | null = null;

  start(socket: Socket): void {
    this.stop();

    this.socket = socket;

    if (!socket.connected) {
      return;
    }

    this.emit();

    this.timer = setInterval(() => {
      this.emit();
    }, SOCKET_HEARTBEAT_INTERVAL);
  }

  stop(): void {
    if (this.timer !== null) {
      clearInterval(this.timer);
      this.timer = null;
    }

    this.socket = null;
  }

  private emit(): void {
    if (!this.socket?.connected) {
      return;
    }

    this.socket.emit("socket_heartbeat");
  }
}

let _socket: Socket | null = null;
let _refCount = 0;
let _heartbeat: SocketHeartbeat | null = null;

function getBaseUrl(): string {
  const wsUrl = import.meta.env.VITE_WS_URL || "ws://localhost:8000/ws/session";

  return wsUrl
    .replace(/^ws:\/\//, "http://")
    .replace(/^wss:\/\//, "https://")
    .replace(/\/ws\/session$/, "");
}

function createSocket(autoConnect = true): Socket {
  const baseUrl = getBaseUrl();

  const socket = io(baseUrl, {
    path: "/ws/session",
    transports: ["websocket"],
    reconnection: true,
    reconnectionAttempts: Infinity,
    reconnectionDelay: 2000,
    reconnectionDelayMax: 30_000,
    withCredentials: true,
    autoConnect,
  });

  return socket;
}

function setupSocketListeners(socket: Socket): void {
  socket.on("connect", () => {
    _heartbeat?.start(socket);
  });

  socket.on("disconnect", () => {
    _heartbeat?.stop();
  });

  socket.on("record_processing_status", (data: any) => {
    window.dispatchEvent(
      new CustomEvent("tendo:record-processing", {
        detail: data,
      }),
    );
  });

  socket.on("snapshot_updated", (data: any) => {
    window.dispatchEvent(
      new CustomEvent("tendo:snapshot-updated", {
        detail: data,
      }),
    );
  });
}

function getSocket(): Socket {
  if (!_socket) {
    _socket = createSocket(true);
    _heartbeat = new SocketHeartbeat();
    setupSocketListeners(_socket);
  }

  return _socket;
}

export function connectSocket(): Socket {
  _refCount++;

  return getSocket();
}

export function disconnectSocket(): void {
  _refCount--;

  if (_refCount <= 0 && _socket) {
    _heartbeat?.stop();

    _socket.disconnect();

    _socket = null;
    _heartbeat = null;
    _refCount = 0;
  }
}

export function emitEvent(event: string, data: any): void {
  const socket = getSocket();

  if (socket.connected) {
    socket.emit(event, data);
  }
}

export function onEvent(event: string, handler: (data: any) => void): void {
  getSocket().on(event, handler);
}

export function offEvent(event: string, handler: (data: any) => void): void {
  getSocket().off(event, handler);
}

export function useSocketEvent(
  event: string,
  handler: (data: any) => void,
  deps: any[] = [],
): void {
  useEffect(() => {
    const socket = connectSocket();

    socket.on(event, handler);

    return () => {
      socket.off(event, handler);

      disconnectSocket();
    };
  }, deps);
}

export class WSClient {
  private socket: Socket | null = null;
  private callbacks: WSCallbacks;
  private heartbeat: SocketHeartbeat | null = null;
  private connectPromise: Promise<void> | null = null;

  constructor(callbacks: WSCallbacks) {
    this.callbacks = callbacks;
  }

  async connect(url: string): Promise<void> {
    if (this.socket?.connected) {
      return;
    }

    if (this.connectPromise) {
      return this.connectPromise;
    }

    const httpUrl = url
      .replace(/^ws:\/\//, "http://")
      .replace(/^wss:\/\//, "https://");

    const urlObj = new URL(httpUrl);

    const path = urlObj.pathname;

    const params = new URLSearchParams(urlObj.search);

    const query: Record<string, string> = {};

    params.forEach((value, key) => {
      query[key] = value;
    });

    this.connectPromise = new Promise((resolve, reject) => {
      const socket = io(urlObj.origin, {
        path,
        query,
        transports: ["websocket"],
        reconnection: true,
        reconnectionAttempts: Infinity,
        reconnectionDelay: 1000,
        reconnectionDelayMax: 30_000,
        timeout: 10_000,
        withCredentials: true,
      });

      this.socket = socket;

      this.heartbeat = new SocketHeartbeat();

      let settled = false;

      socket.on("connect", () => {
        this.heartbeat?.start(socket);

        this.callbacks.onOpen?.();

        if (!settled) {
          settled = true;
          resolve();
        }
      });

      socket.on("message", (data: unknown) => {
        try {
          const msg = typeof data === "string" ? JSON.parse(data) : data;

          if (!msg || typeof msg !== "object") {
            return;
          }

          this.callbacks.onMessage(msg as WSMessage);
        } catch {
          this.callbacks.onError?.("Invalid server message");
        }
      });

      socket.on("disconnect", () => {
        this.heartbeat?.stop();

        this.callbacks.onClose?.();
      });

      socket.on("connect_error", (error) => {
        this.callbacks.onError?.("Connecting...");

        if (!settled) {
          settled = true;
          reject(new Error(error.message));
        }
      });

      socket.io.on("reconnect_attempt", (attempt) => {
        this.callbacks.onReconnecting?.(attempt, Infinity);
      });

      socket.io.on("reconnect", () => {
        this.callbacks.onReconnected?.();
      });
    });

    try {
      await this.connectPromise;
    } finally {
      this.connectPromise = null;
    }
  }

  send(msg: WSMessage): boolean {
    if (!this.socket?.connected) {
      return false;
    }

    this.socket.emit("message", msg);

    return true;
  }

  isOpen(): boolean {
    return this.socket?.connected ?? false;
  }

  close(): void {
    this.heartbeat?.stop();
    this.heartbeat = null;

    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }

    this.connectPromise = null;
  }
}
