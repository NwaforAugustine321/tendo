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
      /*
       * Do not expose the internal LiveKit/agent error.
       */
      set({
        connectionState: "error",
        interactionMode: "text",
        errorMessage: "Session is unavailable.",
        statusText: "Session is unavailable.",
        micActive: false,
        userSpeaking: false,
        agentSpeaking: false,
        agentReady: false,
      });

      toast.error("Audio session is unavailable. Please try again.");
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

      if (isTerminalSessionStatus(status)) {
        stopStatusMonitor();

        client?.stopMic();

        /*
         * The backend says the session is finished.
         * Clean up the client because this is a real
         * terminal session state.
         */
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
       * JS_RUNNING / JS_PENDING / other non-terminal
       * statuses are intentionally left alone.
       *
       * LiveKit remains the source of truth for the
       * actual realtime connection.
       */
    } catch {
      if (monitorVersion !== statusMonitorVersion) {
        return;
      }

      statusCheckFailures += 1;

      /*
       * One temporary status API failure must not
       * terminate an otherwise healthy voice session.
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

      toast.error("Audio session is unavailable. Please try again.");
    } finally {
      statusCheckInFlight = false;
    }
  };

  /*
   * Keep the health check deliberately low frequency.
   *
   * Do not immediately call the status endpoint here.
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
      toast.error("Unable to start audio session.");

      throw new Error("Business ID is required.");
    }

    const version = ++lifecycleVersion;

    stopStatusMonitor();

    set({
      connectionState: "initializing",
      interactionMode: "text",
      errorMessage: "",
      agentReady: false,
      micActive: false,
      userSpeaking: false,
      agentSpeaking: false,
      statusText: "Starting voice...",
    });

    try {
      const session = await initAgent(businessId, requestedSessionId);

      if (version !== lifecycleVersion) {
        throw new Error("Voice initialization was cancelled.");
      }

      const previousClient = client;

      client = null;

      previousClient?.stopMic();
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
        errorMessage: "Unable to start voice.",
        statusText: "Unable to start voice.",
      });

      toast.error("Unable to start audio session. Please try again.");

      throw new Error("Unable to start audio session.");
    }
  },

  /*
   * START VOICE AGENT
   */
  startAgent: async (businessId, sessionId) => {
    if (!businessId) {
      toast.error("Unable to start audio session.");

      throw new Error("Business ID is required.");
    }

    if (!sessionId) {
      toast.error("Unable to start audio session.");

      throw new Error("Session ID is required.");
    }

    let state = get();

    /*
     * Do not block a retry merely because the previous
     * failed attempt left micActive=true.
     *
     * Only return when we genuinely have an active
     * voice interaction.
     */
    if (
      state.micActive &&
      state.agentReady &&
      state.connectionState !== "error"
    ) {
      return;
    }

    /*
     * If a previous failed attempt left the microphone
     * active but the agent is no longer ready, clean
     * that microphone state before retrying.
     */
    if (state.micActive && !state.agentReady) {
      client?.stopMic();

      set({
        micActive: false,
        userSpeaking: false,
        agentSpeaking: false,
      });

      state = get();
    }

    /*
     * If the user's LiveKit connection itself died,
     * we need a fresh client connection and therefore
     * a fresh session/token.
     *
     * This is the case where obtaining a new token is
     * actually necessary.
     */
    if (!client?.isConnected()) {
      stopStatusMonitor();

      try {
        await get().initAgent(businessId, sessionId);
      } catch {
        /*
         * initAgent already handles the user-facing
         * toast and generic state.
         */
        throw new Error("Unable to start voice.");
      }

      state = get();

      if (!client?.isConnected()) {
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

        toast.error("Audio connection is unavailable. Please try again.");

        throw new Error("Audio connection is unavailable.");
      }
    }

    /*
     * A retry must be allowed to explicitly dispatch
     * the agent again.
     *
     * Previously this depended only on isAgentReady(),
     * which could remain stale after a failed agent job.
     */
    const previousStateWasError =
      state.connectionState === "error" || !state.agentReady;

    const version = ++startVersion;

    const activeClient = client;

    if (!activeClient) {
      toast.error("Audio connection is unavailable. Please try again.");

      throw new Error("Audio connection is unavailable.");
    }

    try {
      set({
        connectionState: "waiting_for_agent",
        interactionMode: "listening",
        errorMessage: "",
        statusText: "Starting voice...",
      });

      /*
       * Dispatch again when:
       *
       * - there is no known ready agent, OR
       * - the previous state was an error.
       *
       * This is the important retry fix.
       */
      if (previousStateWasError || !activeClient.isAgentReady()) {
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
        errorMessage: "Unable to start voice.",
        statusText: "Unable to start voice.",
      });

      toast.error("Unable to audio session. Please try again.");

      throw new Error("Unable to start voice.");
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
      throw new Error("Business ID and session ID are required.");
    }

    lifecycleVersion += 1;
    startVersion += 1;

    stopStatusMonitor();

    const version = lifecycleVersion;

    set({
      connectionState: "stopping",
      statusText: "Stopping voice...",
      errorMessage: "",
    });

    try {
      await stopAgentApi(businessId, sessionId);
    } catch {
      /*
       * Do not expose backend/internal errors.
       *
       * We still clean up the local LiveKit session.
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
      toast.error("Voice session is unavailable.");

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
