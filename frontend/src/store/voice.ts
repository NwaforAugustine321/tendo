import { create } from "zustand";
import { LiveKitVoiceClient } from "../lib/livekit-client";
import { request } from "../lib/services/http";

type VoiceConnectionState =
  | "disconnected"
  | "connecting"
  | "connected"
  | "listening"
  | "speaking"
  | "error";

type VoiceSession = {
  token: string;
  url: string;
  room: string;
  session_id: string;
  business_id: string;
  record_id: string;
};

export interface VoiceState {
  connectionState: VoiceConnectionState;
  session: VoiceSession | null;
  errorMessage: string;
  micActive: boolean;
  userSpeaking: boolean;
  agentSpeaking: boolean;
  statusText: string;

  startAgent: (params: {
    businessId: string;
    sessionId?: string;
    recordId?: string;
  }) => Promise<void>;
  stopAgent: () => Promise<void>;
  toggleMic: () => Promise<void>;
  setStatusText: (text: string) => void;
  reset: () => void;
}

let _client: LiveKitVoiceClient | null = null;
let _connectVersion = 0; // Guards against React strict mode race conditions

export const useVoiceStore = create<VoiceState>((set, get) => ({
  connectionState: "disconnected",
  session: null,
  errorMessage: "",
  micActive: false,
  userSpeaking: false,
  agentSpeaking: false,
  statusText: "",

  setStatusText: (text: string) => set({ statusText: text }),

  startAgent: async ({ businessId, sessionId, recordId }) => {
    const { connectionState } = get();

    // Already connected or connecting — skip
    if (
      connectionState === "connected" ||
      connectionState === "listening" ||
      connectionState === "speaking" ||
      connectionState === "connecting"
    )
      return;

    // Increment version to invalidate any in-flight previous attempt
    const version = ++_connectVersion;

    set({ connectionState: "connecting", errorMessage: "" });

    try {
      const data = await request<VoiceSession>("/voice/start/agent", {
        method: "POST",
        body: {
          business_id: businessId,
          session_id: sessionId || "",
          record_id: recordId || "",
        },
        silent: true,
      });

      // If stopAgent was called while we were awaiting, abort
      if (_connectVersion !== version) return;

      set({ session: data });

      const client = new LiveKitVoiceClient({
        onConnected: () => {
          if (_connectVersion === version) {
            set({ connectionState: "connected" });
          }
        },
        onDisconnected: () => {
          if (_client === client) {
            set({
              connectionState: "disconnected",
              micActive: false,
              agentSpeaking: false,
              userSpeaking: false,
            });
            _client = null;
          }
        },
        onAgentReady: () => {
          if (_connectVersion === version) {
            set({ connectionState: "connected" });
          }
        },
        onAgentLeft: () => {},
        onUserSpeakingChange: (speaking) => set({ userSpeaking: speaking }),
        onAgentSpeakingChange: (speaking) => {
          set({ agentSpeaking: speaking });
          if (speaking) {
            set({ connectionState: "speaking", statusText: "" });
          } else if (get().micActive) {
            set({ connectionState: "listening" });
          } else {
            set({ connectionState: "connected" });
          }
        },
        onMessage: (data: any) => {
          if (data?.type === "progress" && data?.payload?.message) {
            set({ statusText: data.payload.message });
          }
        },
        onTranscript: () => {},
        onTurnComplete: () => {
          set({ agentSpeaking: false, statusText: "" });
          if (get().micActive) set({ connectionState: "listening" });
        },
        onError: (err) => {
          set({ errorMessage: err, connectionState: "error" });
        },
      });

      await client.connect(data.url, data.token);

      // Check again after async connect
      if (_connectVersion !== version) {
        client.disconnect();
        return;
      }

      _client = client;
      set({ connectionState: "connected" });
    } catch {
      if (_connectVersion === version) {
        set({
          connectionState: "error",
          errorMessage: "Failed to start voice agent",
        });
      }
    }
  },

  stopAgent: async () => {
    // Invalidate any in-flight startAgent
    _connectVersion++;

    const { session } = get();

    if (_client) {
      _client.stopMic();
      _client.disconnect();
      _client = null;
    }

    set({
      connectionState: "disconnected",
      micActive: false,
      agentSpeaking: false,
      userSpeaking: false,
    });

    if (session) {
      set({ session: null });
      try {
        await request("/voice/stop/agent", {
          method: "POST",
          body: {
            room: session.room,
            session_id: session.session_id,
            business_id: session.business_id,
            record_id: session.record_id,
          },
          silent: true,
        });
      } catch {}
    }
  },

  toggleMic: async () => {
    const { micActive, connectionState } = get();

    if (!_client) return;
    if (connectionState === "disconnected" || connectionState === "connecting")
      return;

    if (micActive) {
      _client.stopMic();
      set({ micActive: false, connectionState: "connected" });
    } else {
      try {
        await _client.startMic();
        set({ micActive: true, connectionState: "listening" });
      } catch (err: any) {
        const msg =
          err?.name === "NotAllowedError"
            ? "Microphone permission denied."
            : "Could not access microphone.";
        set({ errorMessage: msg, connectionState: "error" });
      }
    }
  },

  reset: () => {
    _connectVersion++;
    if (_client) {
      _client.stopMic();
      _client.disconnect();
      _client = null;
    }
    set({
      connectionState: "disconnected",
      session: null,
      errorMessage: "",
      micActive: false,
      userSpeaking: false,
      agentSpeaking: false,
    });
  },
}));
