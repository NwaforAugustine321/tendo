import { create } from "zustand";

import {
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
  businessId: string | null;
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
let startVersion = 0;

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
          };
        }

        return {
          connectionState: "error",
          interactionMode: "text",
          agentReady: false,
          micActive: false,
          userSpeaking: false,
          agentSpeaking: false,
          errorMessage: "Voice connection disconnected.",
          statusText: "Voice connection disconnected.",
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
      set({
        agentReady: false,
        interactionMode: "text",
        agentSpeaking: false,
        micActive: false,
        userSpeaking: false,
        connectionState: "error",
        errorMessage: "Voice agent disconnected.",
        statusText: "Voice agent disconnected.",
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

    onError: (error) => {
      set({
        connectionState: "error",
        interactionMode: "text",
        errorMessage: error,
        statusText: error,
        micActive: false,
        userSpeaking: false,
        agentSpeaking: false,
      });
    },
  });
}

export const useVoiceAgentStore = create<VoiceStore>((set, get) => ({
  connectionState: "disconnected",
  interactionMode: "text",
  businessId: null,
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

    if (current.session?.business_id === businessId && client?.isConnected()) {
      return;
    }

    const version = ++lifecycleVersion;

    set({
      businessId,
      connectionState: "initializing",
      interactionMode: "text",
      errorMessage: "",
      agentReady: false,
      micActive: false,
      userSpeaking: false,
      agentSpeaking: false,
      statusText: "Initializing voice...",
    });

    try {
      const session = await initAgent(businessId, requestedSessionId);

      if (version !== lifecycleVersion) {
        return;
      }

      const previousClient = client;

      client = null;

      previousClient?.disconnect();

      const nextClient = createClient(set);

      client = nextClient;

      set({
        businessId: session.business_id,
        session,
        connectionState: "connecting",
        interactionMode: "text",
        agentReady: false,
        micActive: false,
        userSpeaking: false,
        agentSpeaking: false,
        errorMessage: "",
        statusText: "Connecting...",
      });

      await nextClient.connect(session.url, session.token);

      if (version !== lifecycleVersion) {
        nextClient.disconnect();
        return;
      }

      set({
        connectionState: "ready",
        interactionMode: "text",
        agentReady: false,
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
        error instanceof Error ? error.message : "Failed to initialize voice.";

      set({
        businessId,
        connectionState: "error",
        interactionMode: "text",
        agentReady: false,
        micActive: false,
        userSpeaking: false,
        agentSpeaking: false,
        errorMessage: message,
        statusText: message,
      });

      throw error;
    }
  },

  startAgent: async () => {
    const state = get();

    if (state.micActive) {
      return;
    }

    if (!state.session) {
      return;
    }

    if (!client?.isConnected()) {
      return;
    }

    const version = ++startVersion;
    const activeClient = client;
    const session = state.session;

    try {
      set({
        connectionState: "waiting_for_agent",
        interactionMode: "listening",
        errorMessage: "",
        statusText: "Starting agent...",
      });

      if (!activeClient.isAgentReady()) {
        await startAgentApi(session.business_id, session.session_id);

        if (version !== startVersion) {
          return;
        }
      }

      if (!activeClient.isConnected()) {
        throw new Error("Voice connection is no longer available.");
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
    } catch (error) {
      if (version !== startVersion) {
        return;
      }

      const message =
        error instanceof Error ? error.message : "Failed to start voice agent.";

      activeClient.stopMic();

      set({
        connectionState: "error",
        interactionMode: "text",
        agentReady: false,
        micActive: false,
        userSpeaking: false,
        agentSpeaking: false,
        errorMessage: message,
        statusText: message,
      });

      throw error;
    }
  },

  stopMic: () => {
    const state = get();

    if (!state.micActive) {
      return;
    }

    client?.stopMic();

    const agentReady = state.agentReady && client?.isConnected();

    set({
      micActive: false,
      userSpeaking: false,
      agentSpeaking: false,
      interactionMode: "text",
      connectionState: agentReady ? "ready" : "error",
      statusText: agentReady ? "Ready" : "Voice agent unavailable.",
    });
  },

  stopAgent: async () => {
    lifecycleVersion += 1;
    startVersion += 1;

    const state = get();

    if (!state.session) {
      client?.disconnect();
      client = null;

      set({
        connectionState: "disconnected",
        interactionMode: "text",
        businessId: null,
        session: null,
        errorMessage: "",
        agentReady: false,
        micActive: false,
        userSpeaking: false,
        agentSpeaking: false,
        statusText: "Disconnected",
      });

      return;
    }

    const session = state.session;
    const version = lifecycleVersion;

    set({
      connectionState: "stopping",
      statusText: "Stopping...",
    });

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
        interactionMode: "text",
        businessId: null,
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

    const state = get();

    if (!state.agentReady || !client?.isConnected()) {
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
    startVersion += 1;

    client?.disconnect();
    client = null;

    set({
      connectionState: "disconnected",
      interactionMode: "text",
      businessId: null,
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
