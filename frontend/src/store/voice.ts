import { create } from "zustand";
import { toast } from "sonner";

import {
  getAgentSessionStatus,
  initAgent,
  startAgent as startAgentApi,
  stopAgent as stopAgentApi,
} from "../lib/voice-agent/api";

import { LiveKitVoiceClient } from "../lib/voice-agent/client";

import type {
  VoiceConnectionState,
  VoiceInteractionMode,
  VoiceSession,
} from "../lib/voice-agent/types";

type VoiceStore = {
  connectionState: VoiceConnectionState;
  interactionMode: VoiceInteractionMode;
  errorMessage: string;
  agentReady: boolean;
  micActive: boolean;
  userSpeaking: boolean;
  agentSpeaking: boolean;
  statusText: string;

  initAgent: (businessId: string, sessionId?: string) => Promise<VoiceSession>;

  startAgent: (businessId: string, sessionId: string) => Promise<void>;

  stopMic: () => void;

  stopAgent: (businessId: string, sessionId: string) => Promise<void>;

  sendPrompt: (text: string) => boolean;

  setStatusText: (text: string) => void;
  reset: () => void;
};

const SESSION_STATUS_INTERVAL_MS = 30000;

const MAX_STATUS_CHECK_FAILURES = 2;

const TERMINAL_SESSION_STATUSES = new Set([
  "JS_SUCCESS",
  "JS_FAILED",
  "JS_CANCELLED",
  "JS_CANCELED",
  "SUCCESS",
  "FAILED",
  "CANCELLED",
  "CANCELED",
  "STOPPED",
  "ENDED",
  "ERROR",
]);

let client: LiveKitVoiceClient | null = null;

let lifecycleVersion = 0;
let startVersion = 0;

let statusMonitorTimer: ReturnType<typeof setInterval> | null = null;

let statusCheckInFlight = false;

let statusCheckFailures = 0;

let statusMonitorVersion = 0;

function stopStatusMonitor(): void {
  statusMonitorVersion += 1;

  if (statusMonitorTimer) {
    clearInterval(statusMonitorTimer);
    statusMonitorTimer = null;
  }

  statusCheckInFlight = false;
  statusCheckFailures = 0;
}

function normalizeStatus(value: unknown): string {
  if (value === null || value === undefined) {
    return "";
  }

  return String(value).trim().toUpperCase();
}

function isTerminalSessionStatus(value: unknown): boolean {
  return TERMINAL_SESSION_STATUSES.has(normalizeStatus(value));
}

function createClient(
  set: (
    partial: Partial<VoiceStore> | ((state: VoiceStore) => Partial<VoiceStore>),
  ) => void,
): LiveKitVoiceClient {
  return new LiveKitVoiceClient({
    onConnected: () => {
      set((state) => {
        if (state.connectionState === "stopping") {
          return {};
        }

        return {
          connectionState: "ready",
          statusText: "Ready",
          errorMessage: "",
        };
      });
    },

    onDisconnected: () => {
      set((state) => {
        if (state.connectionState === "stopping") {
          return {
            connectionState: "disconnected",
            interactionMode: "text",
            agentReady: false,
            micActive: false,
            userSpeaking: false,
            agentSpeaking: false,
            statusText: "Disconnected",
            errorMessage: "",
          };
        }

        return {
          connectionState: "error",
          interactionMode: "text",
          agentReady: false,
          micActive: false,
          userSpeaking: false,
          agentSpeaking: false,
          errorMessage: "Session is unavailable.",
          statusText: "Session is unavailable.",
        };
      });
    },

    onAgentReady: () => {
      set((state) => ({
        agentReady: true,
        connectionState: state.micActive ? "listening" : "ready",
        interactionMode: state.micActive ? "listening" : state.interactionMode,
        statusText: state.micActive ? "Listening..." : "Ready",
        errorMessage: "",
      }));
    },

    onAgentLeft: () => {
      stopStatusMonitor();

      set({
        agentReady: false,
        interactionMode: "text",
        agentSpeaking: false,
        micActive: false,
        userSpeaking: false,
        connectionState: "error",
        errorMessage: "Session is unavailable.",
        statusText: "Session is unavailable.",
      });

      toast.error("Session has ended.");
    },

    onUserSpeakingChange: (speaking) => {
      set({
        userSpeaking: speaking,
      });
    },

    onAgentSpeakingChange: (speaking) => {
      set({
        agentSpeaking: speaking,
        interactionMode: speaking ? "speaking" : "listening",
        connectionState: speaking ? "speaking" : "listening",
        statusText: speaking ? "Speaking..." : "Listening...",
      });
    },

    onTranscript: () => {},

    onMessage: () => {},

    onTurnComplete: () => {
      set((state) => ({
        connectionState: state.micActive ? "listening" : "ready",
        interactionMode: state.micActive ? "listening" : "text",
        agentSpeaking: false,
        statusText: state.micActive ? "Listening..." : "Ready",
      }));
    },

    onError: () => {
      set({
        connectionState: "error",
        interactionMode: "text",
        errorMessage: "Session is unavailable.",
        statusText: "Session is unavailable.",
        micActive: false,
        userSpeaking: false,
        agentSpeaking: false,
      });

      toast.error("Session is unavailable.");
    },
  });
}

function startStatusMonitor(
  businessId: string,
  sessionId: string,
  set: (
    partial: Partial<VoiceStore> | ((state: VoiceStore) => Partial<VoiceStore>),
  ) => void,
): void {
  stopStatusMonitor();

  const monitorVersion = statusMonitorVersion;

  const checkStatus = async () => {
    if (monitorVersion !== statusMonitorVersion) {
      return;
    }

    if (statusCheckInFlight) {
      return;
    }

    if (!client?.isConnected()) {
      return;
    }

    statusCheckInFlight = true;

    try {
      const result = await getAgentSessionStatus(businessId, sessionId);

      if (monitorVersion !== statusMonitorVersion) {
        return;
      }

      statusCheckFailures = 0;

      const status = normalizeStatus(
        (
          result as {
            status?: unknown;
          }
        )?.status,
      );

      /*
       * The backend session is no longer active.
       */
      if (isTerminalSessionStatus(status)) {
        stopStatusMonitor();

        client?.stopMic();
        client?.disconnect();
        client = null;

        set({
          connectionState: "disconnected",
          interactionMode: "text",
          agentReady: false,
          micActive: false,
          userSpeaking: false,
          agentSpeaking: false,
          errorMessage: "",
          statusText: "Session has ended.",
        });

        return;
      }

      /*
       * JS_RUNNING / JS_PENDING / other
       * non-terminal states are left alone.
       *
       * LiveKit remains the source of truth
       * for the actual connection state.
       */
    } catch {
      if (monitorVersion !== statusMonitorVersion) {
        return;
      }

      statusCheckFailures += 1;

      /*
       * Do not immediately kill the voice session
       * because of one temporary status API failure.
       */
      if (statusCheckFailures < MAX_STATUS_CHECK_FAILURES) {
        return;
      }

      stopStatusMonitor();

      client?.stopMic();
      client?.disconnect();
      client = null;

      set({
        connectionState: "error",
        interactionMode: "text",
        agentReady: false,
        micActive: false,
        userSpeaking: false,
        agentSpeaking: false,
        errorMessage: "Session is unavailable.",
        statusText: "Session is unavailable.",
      });

      toast.error("Session is unavailable. Please try again.");
    } finally {
      statusCheckInFlight = false;
    }
  };

  /*
   * Do not make an immediate status request here.
   *
   * init/start already confirmed the session.
   * The first health check happens after the
   * low-frequency interval.
   */
  statusMonitorTimer = setInterval(() => {
    void checkStatus();
  }, SESSION_STATUS_INTERVAL_MS);
}

export const useVoiceAgentStore = create<VoiceStore>((set, get) => ({
  connectionState: "disconnected",
  interactionMode: "text",
  errorMessage: "",
  agentReady: false,
  micActive: false,
  userSpeaking: false,
  agentSpeaking: false,
  statusText: "Disconnected",

  /*
   * INITIALIZE VOICE
   */
  initAgent: async (businessId, requestedSessionId) => {
    if (!businessId) {
      toast.error("Unable to start Session.");

      throw new Error("Business ID is required.");
    }

    const version = ++lifecycleVersion;

    set({
      connectionState: "initializing",
      interactionMode: "text",
      errorMessage: "",
      agentReady: false,
      micActive: false,
      userSpeaking: false,
      agentSpeaking: false,
      statusText: "Starting Session...",
    });

    try {
      const session = await initAgent(businessId, requestedSessionId);

      if (version !== lifecycleVersion) {
        throw new Error("Voice initialization was cancelled.");
      }

      const previousClient = client;

      client = null;

      previousClient?.disconnect();

      const nextClient = createClient(set);

      client = nextClient;

      set({
        connectionState: "connecting",
        interactionMode: "text",
        agentReady: false,
        micActive: false,
        userSpeaking: false,
        agentSpeaking: false,
        errorMessage: "",
        statusText: "Connecting to voice...",
      });

      await nextClient.connect(session.url, session.token);

      if (version !== lifecycleVersion) {
        nextClient.disconnect();

        throw new Error("Voice initialization was cancelled.");
      }

      set({
        connectionState: "ready",
        interactionMode: "text",
        agentReady: false,
        statusText: "Ready",
        errorMessage: "",
      });

      return session;
    } catch {
      if (version !== lifecycleVersion) {
        throw new Error("Voice initialization was cancelled.");
      }

      client?.disconnect();
      client = null;

      stopStatusMonitor();

      set({
        connectionState: "error",
        interactionMode: "text",
        agentReady: false,
        micActive: false,
        userSpeaking: false,
        agentSpeaking: false,
        errorMessage: "Unable to start Session.",
        statusText: "Unable to start Session.",
      });

      toast.error("Unable to start Session. Please try again.");

      throw new Error("Unable to start Session.");
    }
  },

  /*
   * START VOICE AGENT
   */
  startAgent: async (businessId, sessionId) => {
    if (!businessId) {
      toast.error("Unable to start Session.");

      throw new Error("Business ID is required.");
    }

    if (!sessionId) {
      toast.error("Unable to start Session.");

      throw new Error("Session ID is required.");
    }

    const state = get();

    if (state.micActive) {
      return;
    }

    if (!client?.isConnected()) {
      toast.error("Voice connection is unavailable. Please try again.");

      throw new Error("Voice connection is unavailable.");
    }

    const version = ++startVersion;

    const activeClient = client;

    try {
      set({
        connectionState: "waiting_for_agent",
        interactionMode: "listening",
        errorMessage: "",
        statusText: "Starting Session...",
      });

      if (!activeClient.isAgentReady()) {
        await startAgentApi(businessId, sessionId);

        if (version !== startVersion) {
          return;
        }
      }

      if (!activeClient.isConnected()) {
        throw new Error("Voice connection is unavailable.");
      }

      set({
        connectionState: "listening",
        interactionMode: "listening",
        statusText: "Starting microphone...",
        errorMessage: "",
      });

      await activeClient.startMic();

      if (version !== startVersion) {
        activeClient.stopMic();
        return;
      }

      set({
        micActive: true,
        connectionState: "listening",
        interactionMode: "listening",
        statusText: "Listening...",
        errorMessage: "",
      });

      /*
       * Start the low-frequency session
       * health monitor only after voice has
       * successfully started.
       */
      startStatusMonitor(businessId, sessionId, set);
    } catch {
      if (version !== startVersion) {
        return;
      }

      activeClient.stopMic();

      stopStatusMonitor();

      set({
        connectionState: "error",
        interactionMode: "text",
        agentReady: false,
        micActive: false,
        userSpeaking: false,
        agentSpeaking: false,
        errorMessage: "Unable to start Session.",
        statusText: "Unable to start Session.",
      });

      toast.error("Unable to start Session. Please try again.");

      throw new Error("Unable to start Session.");
    }
  },

  /*
   * STOP MICROPHONE
   */
  stopMic: () => {
    const state = get();

    if (!state.micActive) {
      return;
    }

    client?.stopMic();

    set({
      micActive: false,
      userSpeaking: false,
      agentSpeaking: false,
      interactionMode: "text",
      connectionState: client?.isConnected() ? "ready" : "error",
      statusText: client?.isConnected() ? "Ready" : "Session is unavailable.",
      errorMessage: client?.isConnected() ? "" : "Session is unavailable.",
    });
  },

  /*
   * STOP VOICE AGENT
   */
  stopAgent: async (businessId, sessionId) => {
    if (!businessId || !sessionId) {
      toast.error("Unable to stop Session.");

      throw new Error("Business ID and session ID are required.");
    }

    lifecycleVersion += 1;
    startVersion += 1;

    stopStatusMonitor();

    const version = lifecycleVersion;

    set({
      connectionState: "stopping",
      statusText: "Stopping Session...",
      errorMessage: "",
    });

    try {
      await stopAgentApi(businessId, sessionId);
    } catch {
      /*
       * Even if the backend stop request fails,
       * clean up the local voice connection.
       *
       * Do not expose the backend error.
       */
    } finally {
      if (version !== lifecycleVersion) {
        return;
      }

      client?.stopMic();
      client?.disconnect();
      client = null;

      set({
        connectionState: "disconnected",
        interactionMode: "text",
        errorMessage: "",
        agentReady: false,
        micActive: false,
        userSpeaking: false,
        agentSpeaking: false,
        statusText: "Disconnected",
      });
    }
  },

  /*
   * SEND PROMPT
   */
  sendPrompt: (text) => {
    if (!text.trim()) {
      return false;
    }

    const state = get();

    if (!state.agentReady || !client?.isConnected()) {
      toast.error("Session is unavailable.");

      return false;
    }

    return client.sendPrompt(text);
  },

  setStatusText: (text) => {
    set({
      statusText: text,
    });
  },

  /*
   * RESET
   */
  reset: () => {
    lifecycleVersion += 1;
    startVersion += 1;

    stopStatusMonitor();

    client?.stopMic();
    client?.disconnect();
    client = null;

    set({
      connectionState: "disconnected",
      interactionMode: "text",
      errorMessage: "",
      agentReady: false,
      micActive: false,
      userSpeaking: false,
      agentSpeaking: false,
      statusText: "Disconnected",
    });
  },
}));
