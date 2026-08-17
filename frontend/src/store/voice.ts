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
let _reconnectAttempts = 0;
let _reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let _agentReadyTimeout: ReturnType<typeof setTimeout> | null = null;
const MAX_RECONNECT_ATTEMPTS = 10;
const RECONNECT_BASE_DELAY_MS = 3000;

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
            set({ connectionState: "connected", statusText: "" });
            // Agent is back — cancel any pending reconnect and reset counter
            if (_reconnectTimer) {
              clearTimeout(_reconnectTimer);
              _reconnectTimer = null;
            }
            if (_agentReadyTimeout) {
              clearTimeout(_agentReadyTimeout);
              _agentReadyTimeout = null;
            }
            _reconnectAttempts = 0;
          }
        },
        onAgentLeft: () => {
          // Agent left unexpectedly — attempt auto-reconnect
          const { connectionState } = get();
          if (connectionState === "disconnected" || connectionState === "error")
            return;

          // Already reconnecting — don't fire again
          if (_reconnectTimer) return;

          if (_reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
            set({
              connectionState: "error",
              errorMessage: "Voice agent unavailable. Please try again.",
              agentSpeaking: false,
            });
            _reconnectAttempts = 0;
            return;
          }

          _reconnectAttempts++;
          const delay =
            RECONNECT_BASE_DELAY_MS * Math.pow(2, _reconnectAttempts - 1);

          set({
            statusText: `reconnecting...`,
            agentSpeaking: false,
          });

          if (_reconnectTimer) clearTimeout(_reconnectTimer);
          _reconnectTimer = setTimeout(async () => {
            _reconnectTimer = null;
            try {
              await request("/voice/start/agent", {
                method: "POST",
                body: {
                  business_id: businessId,
                  session_id: sessionId || "",
                  record_id: recordId || "",
                },
                silent: true,
              });
            } catch {
              // If dispatch fails, the next ParticipantDisconnected or
              // timeout will retry until MAX_RECONNECT_ATTEMPTS
              const { connectionState: currentState } = get();
              if (
                currentState !== "disconnected" &&
                _reconnectAttempts < MAX_RECONNECT_ATTEMPTS
              ) {
                // Trigger another attempt
                get().startAgent({ businessId, sessionId, recordId });
              } else {
                set({
                  connectionState: "error",
                  errorMessage: "Voice agent unavailable. Please try again.",
                });
              }
            }
          }, delay);
        },
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

      // If agent doesn't become ready within 15s, trigger reconnect with exponential backoff
      const scheduleAgentCheck = () => {
        const checkDelay = Math.min(
          15000 * Math.pow(2, _reconnectAttempts),
          60000,
        );
        _agentReadyTimeout = setTimeout(async () => {
          _agentReadyTimeout = null;
          if (
            _connectVersion !== version ||
            _client !== client ||
            client.isAgentReady()
          ) {
            return;
          }

          if (_reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
            set({
              connectionState: "error",
              errorMessage: "Voice agent unavailable. Please try again.",
            });
            return;
          }

          _reconnectAttempts++;
          set({
            statusText: `reconnecting...`,
          });

          try {
            await request("/voice/start/agent", {
              method: "POST",
              body: {
                business_id: businessId,
                session_id: sessionId || "",
                record_id: recordId || "",
              },
              silent: true,
            });
          } catch {}

          // Wait with exponential backoff before next check
          const waitDelay = Math.min(
            15000 * Math.pow(2, _reconnectAttempts - 1),
            60000,
          );
          _agentReadyTimeout = setTimeout(() => {
            _agentReadyTimeout = null;
            if (
              _connectVersion === version &&
              _client === client &&
              !client.isAgentReady()
            ) {
              scheduleAgentCheck();
            }
          }, waitDelay);
        }, checkDelay);
      };

      scheduleAgentCheck();
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

    // Cancel any pending reconnect
    if (_reconnectTimer) {
      clearTimeout(_reconnectTimer);
      _reconnectTimer = null;
    }
    if (_agentReadyTimeout) {
      clearTimeout(_agentReadyTimeout);
      _agentReadyTimeout = null;
    }
    _reconnectAttempts = 0;

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
    const { micActive, connectionState, session } = get();

    // If already listening, stop mic
    if (micActive && _client) {
      _client.stopMic();
      set({ micActive: false, connectionState: "connected" });
      return;
    }

    // If no client but we have session data (token/url/room), connect first
    if (!_client && session?.token && session?.url) {
      set({ connectionState: "connecting", errorMessage: "" });
      const version = ++_connectVersion;

      try {
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
              set({ connectionState: "connected", statusText: "" });
              if (_reconnectTimer) {
                clearTimeout(_reconnectTimer);
                _reconnectTimer = null;
              }
              _reconnectAttempts = 0;
            }
          },
          onAgentLeft: () => {
            const { connectionState: cs, session: sess } = get();
            if (cs === "disconnected" || cs === "error") return;

            // Already reconnecting — don't fire again
            if (_reconnectTimer) return;

            if (_reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
              set({
                connectionState: "error",
                errorMessage: "Voice agent unavailable. Please try again.",
                agentSpeaking: false,
              });
              _reconnectAttempts = 0;
              return;
            }

            _reconnectAttempts++;
            const delay =
              RECONNECT_BASE_DELAY_MS * Math.pow(2, _reconnectAttempts - 1);

            set({
              statusText: `reconnecting...`,
              agentSpeaking: false,
            });

            if (_reconnectTimer) clearTimeout(_reconnectTimer);
            _reconnectTimer = setTimeout(async () => {
              _reconnectTimer = null;
              if (!sess) return;
              try {
                await request("/voice/start/agent", {
                  method: "POST",
                  body: {
                    business_id: sess.business_id,
                    session_id: sess.session_id || "",
                    record_id: sess.record_id || "",
                  },
                  silent: true,
                });
              } catch {
                set({
                  connectionState: "error",
                  errorMessage: "Voice agent unavailable. Please try again.",
                });
              }
            }, delay);
          },
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

        await client.connect(session.url, session.token);

        if (_connectVersion !== version) {
          client.disconnect();
          return;
        }

        _client = client;
        set({ connectionState: "connected" });

        // Now start mic
        await _client.startMic();
        set({ micActive: true, connectionState: "listening" });
      } catch (err: any) {
        const msg =
          err?.name === "NotAllowedError"
            ? "Microphone permission denied."
            : "Could not connect voice.";
        set({ errorMessage: msg, connectionState: "error" });
      }
      return;
    }

    // If no client and no session, call /voice/start/agent first
    if (!_client && !session) {
      // Need businessId from somewhere — use the import
      const { useBusinessStore } = await import("./business");
      const businessId = useBusinessStore.getState().currentProfile?.id || "";
      if (!businessId) {
        set({ errorMessage: "No business profile", connectionState: "error" });
        return;
      }

      // startAgent will connect and set _client
      await get().startAgent({ businessId });

      // After startAgent completes, try to start mic
      if (_client) {
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
      return;
    }

    // Client exists, just toggle mic on
    if (_client && !micActive) {
      if (
        connectionState === "disconnected" ||
        connectionState === "connecting"
      )
        return;

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
    if (_reconnectTimer) {
      clearTimeout(_reconnectTimer);
      _reconnectTimer = null;
    }
    if (_agentReadyTimeout) {
      clearTimeout(_agentReadyTimeout);
      _agentReadyTimeout = null;
    }
    _reconnectAttempts = 0;
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
