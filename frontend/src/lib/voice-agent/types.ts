export type VoiceConnectionState =
  | "disconnected"
  | "initializing"
  | "connecting"
  | "waiting_for_agent"
  | "ready"
  | "listening"
  | "speaking"
  | "reconnecting"
  | "stopping"
  | "error";

export type VoiceInteractionMode = "text" | "listening" | "speaking";

export type VoiceSession = {
  token: string;
  url: string;
  room: string;
  session_id: string;
  business_id: string;
};

export type VoiceInitResponse = VoiceSession;

export type VoiceAgentJobStatus =
  | "JS_PENDING"
  | "JS_RUNNING"
  | "JS_SUCCESS"
  | "JS_FAILED"
  | "JS_CANCELED";

export type VoiceAgentState = "listening" | "thinking" | "speaking" | null;

export type VoiceAgentJob = {
  id: string;
  dispatch_id: string;
  status: VoiceAgentJobStatus | null;
  error: string | null;
  started_at: number | null;
  ended_at: number | null;
  updated_at: number | null;
  participant_identity: string | null;
  worker_id: string | null;
  agent_id: string | null;
};

export type VoiceAgentDispatch = {
  id: string;
  agent_name: string;
  room: string;
  metadata: string | null;
  created_at: number | null;
  deleted_at: number | null;
};

export type VoiceSessionStatus = {
  dispatch: VoiceAgentDispatch | null;
  job: VoiceAgentJob | null;
  session_status: VoiceAgentJobStatus | null;
  agent_state: VoiceAgentState;
  agent_id: string | null;
  session_error: string | null;
};

export type VoiceDataMessage =
  | {
      type: "transcript";
      data: string;
    }
  | {
      type: "message";
      data: unknown;
    }
  | {
      type: "turn_complete";
      data?: unknown;
    }
  | {
      type: "error";
      data: string;
    };

export type VoiceClientCallbacks = {
  onConnected: () => void;
  onDisconnected: () => void;
  onAgentReady: () => void;
  onAgentLeft: () => void;
  onUserSpeakingChange: (speaking: boolean) => void;
  onAgentSpeakingChange: (speaking: boolean) => void;
  onTranscript: (text: string) => void;
  onMessage: (data: unknown) => void;
  onTurnComplete: () => void;
  onError: (error: string) => void;
};
