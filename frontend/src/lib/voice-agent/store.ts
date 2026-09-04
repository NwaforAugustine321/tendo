import { create } from "zustand";

import {
  getAgentSessionStatus,
  initAgent,
  startAgent as startAgentApi,
  stopAgent as stopAgentApi,
} from "./api";

import { LiveKitVoiceClient } from "./client";

import type { VoiceConnectionState, VoiceSession } from "./types";

type VoiceStore = {
  connectionState: VoiceConnectionState;
  session: VoiceSession | null;
  errorMessage: string;
  agentReady: boolean;
  micActive: boolean;
  userSpeaking: boolean;
  agentSpeaking: boolean;
  statusText: string;

  initAgent: (businessId: string, sessionId?: string) => Promise<void>;

  startAgent: () => Promise<void>;
  stopMic: () => void;
  stopAgent: () => Promise<void>;
  sendPrompt: (text: string) => boolean;

  setStatusText: (text: string) => void;
  reset: () => void;
};

let client: LiveKitVoiceClient | null = null;
let lifecycleVersion = 0;

function createClient(
  set: (
    partial: Partial<VoiceStore> | ((state: VoiceStore) => Partial<VoiceStore>),
  ) => void,
): LiveKitVoiceClient {
  return new LiveKitVoiceClient({
    onConnected: () => {
      set({
        connectionState: "waiting_for_agent",
        statusText: "Connecting to agent...",
      });
    },

    onDisconnected: () => {
      set((state) => ({
        connectionState:
          state.connectionState === "stopping"
            ? "disconnected"
            : "reconnecting",
        agentReady: false,
        micActive: false,
        agentSpeaking: false,
        statusText:
          state.connectionState === "stopping"
            ? "Disconnected"
            : "Reconnecting...",
      }));
    },

    onAgentReady: () => {
      set({
        agentReady: true,
        connectionState: "ready",
        statusText: "Ready",
      });
    },

    onAgentLeft: () => {
      set({
        agentReady: false,
        agentSpeaking: false,
        connectionState: "reconnecting",
        statusText: "Agent disconnected",
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
        connectionState: speaking ? "speaking" : "listening",
        statusText: speaking ? "Speaking..." : "Listening...",
      });
    },

    onTranscript: () => {},

    onMessage: () => {},

    onTurnComplete: () => {
      set((state) => ({
        connectionState: state.micActive ? "listening" : "ready",
        agentSpeaking: false,
        statusText: state.micActive ? "Listening..." : "Ready",
      }));
    },

    onError: (error) => {
      set({
        connectionState: "error",
        errorMessage: error,
        statusText: error,
      });
    },
  });
}

async function waitForAgent(
  businessId: string,
  sessionId: string,
  version: number,
  timeout = 30000,
): Promise<void> {
  const startedAt = Date.now();

  while (Date.now() - startedAt < timeout) {
    if (version !== lifecycleVersion) {
      throw new Error("Voice initialization was cancelled.");
    }

    if (client?.isAgentReady()) {
      return;
    }

    try {
      const status = await getAgentSessionStatus(businessId, sessionId);

      if (version !== lifecycleVersion) {
        throw new Error("Voice initialization was cancelled.");
      }

      if (
        status.session_status === "JS_FAILED" ||
        status.session_status === "JS_CANCELED"
      ) {
        throw new Error(status.session_error || "Voice agent failed to start.");
      }

      if (
        status.agent_state === "listening" ||
        status.agent_state === "speaking"
      ) {
        return;
      }
    } catch (error) {
      if (
        error instanceof Error &&
        error.message === "Voice initialization was cancelled."
      ) {
        throw error;
      }

      throw error;
    }

    await new Promise((resolve) => setTimeout(resolve, 1000));
  }

  throw new Error("Voice agent did not become ready.");
}

export const useVoiceAgentStore = create<VoiceStore>((set, get) => ({
  connectionState: "disconnected",
  session: null,
  errorMessage: "",
  agentReady: false,
  micActive: false,
  userSpeaking: false,
  agentSpeaking: false,
  statusText: "Disconnected",

  initAgent: async (businessId, requestedSessionId) => {
    if (!businessId) {
      throw new Error("Business ID is required.");
    }

    const current = get();

    if (
      current.session?.business_id === businessId &&
      current.agentReady &&
      client?.isConnected()
    ) {
      return;
    }

    const version = ++lifecycleVersion;

    set({
      connectionState: "initializing",
      errorMessage: "",
      agentReady: false,
      statusText: "Initializing voice...",
    });

    try {
      const session = await initAgent(businessId, requestedSessionId);

      if (version !== lifecycleVersion) {
        return;
      }

      client?.disconnect();

      client = createClient(set);

      set({
        session,
        connectionState: "connecting",
        statusText: "Connecting...",
      });

      await client.connect(session.url, session.token);

      if (version !== lifecycleVersion) {
        return;
      }

      await startAgentApi(session.business_id, session.session_id);

      if (version !== lifecycleVersion) {
        return;
      }

      set({
        connectionState: "waiting_for_agent",
        statusText: "Starting agent...",
      });

      await waitForAgent(session.business_id, session.session_id, version);

      if (version !== lifecycleVersion) {
        return;
      }

      set({
        connectionState: "ready",
        agentReady: true,
        statusText: "Ready",
        errorMessage: "",
      });
    } catch (error) {
      if (version !== lifecycleVersion) {
        return;
      }

      client?.disconnect();
      client = null;

      const message =
        error instanceof Error
          ? error.message
          : "Failed to initialize voice agent.";

      set({
        connectionState: "error",
        session: null,
        agentReady: false,
        micActive: false,
        agentSpeaking: false,
        errorMessage: message,
        statusText: message,
      });

      throw error;
    }
  },

  startAgent: async () => {
    const state = get();

    if (!state.session) {
      throw new Error("Voice agent is not initialized.");
    }

    if (!client?.isConnected()) {
      throw new Error("Voice connection is not ready.");
    }

    if (!state.agentReady) {
      throw new Error("Voice agent is not ready.");
    }

    if (state.micActive) {
      return;
    }

    set({
      connectionState: "listening",
      statusText: "Starting microphone...",
      errorMessage: "",
    });

    try {
      await client.startMic();

      set({
        micActive: true,
        connectionState: "listening",
        statusText: "Listening...",
      });
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to start microphone.";

      set({
        connectionState: "error",
        errorMessage: message,
        statusText: message,
      });

      throw error;
    }
  },

  stopMic: () => {
    client?.stopMic();

    set({
      micActive: false,
      userSpeaking: false,
      agentSpeaking: false,
      connectionState: get().agentReady ? "ready" : "disconnected",
      statusText: get().agentReady ? "Ready" : "Disconnected",
    });
  },

  stopAgent: async () => {
    const state = get();

    if (!state.session) {
      client?.disconnect();
      client = null;

      set({
        connectionState: "disconnected",
        agentReady: false,
        micActive: false,
        userSpeaking: false,
        agentSpeaking: false,
        statusText: "Disconnected",
      });

      return;
    }

    const version = ++lifecycleVersion;

    set({
      connectionState: "stopping",
      statusText: "Stopping...",
    });

    const session = state.session;

    try {
      await stopAgentApi(session.business_id, session.session_id);
    } finally {
      if (version !== lifecycleVersion) {
        return;
      }

      client?.disconnect();
      client = null;

      set({
        connectionState: "disconnected",
        session: null,
        errorMessage: "",
        agentReady: false,
        micActive: false,
        userSpeaking: false,
        agentSpeaking: false,
        statusText: "Disconnected",
      });
    }
  },

  sendPrompt: (text) => {
    if (!text.trim()) {
      return false;
    }

    if (!client?.isConnected()) {
      return false;
    }

    if (!get().agentReady) {
      return false;
    }

    return client.sendPrompt(text);
  },

  setStatusText: (text) => {
    set({
      statusText: text,
    });
  },

  reset: () => {
    lifecycleVersion += 1;

    client?.disconnect();
    client = null;

    set({
      connectionState: "disconnected",
      session: null,
      errorMessage: "",
      agentReady: false,
      micActive: false,
      userSpeaking: false,
      agentSpeaking: false,
      statusText: "Disconnected",
    });
  },
}));
