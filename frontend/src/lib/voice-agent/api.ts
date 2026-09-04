import { request } from "../services/http";

import type { VoiceInitResponse, VoiceSessionStatus } from "./types";

const VOICE_AGENT_API_URL =
  import.meta.env.VITE_VOICE_AGENT_URL ?? "http://localhost:8001";

export async function initAgent(
  businessId: string,
  sessionId?: string,
): Promise<VoiceInitResponse> {
  return request<VoiceInitResponse>("/voice/init/agent", {
    method: "POST",
    body: {
      business_id: businessId,
      session_id: sessionId ?? "",
    },
  });
}

export async function startAgent(
  businessId: string,
  sessionId: string,
): Promise<VoiceSessionStatus> {
  return request<VoiceSessionStatus>("/agent/start", {
    method: "POST",
    body: {
      business_id: businessId,
      session_id: sessionId,
    },
    baseUrl: VOICE_AGENT_API_URL,
  });
}

export async function getAgentSessionStatus(
  businessId: string,
  sessionId: string,
): Promise<VoiceSessionStatus> {
  const params = new URLSearchParams({
    business_id: businessId,
    session_id: sessionId,
  });

  return request<VoiceSessionStatus>(
    `/agent/session/status?${params.toString()}`,
    {
      baseUrl: VOICE_AGENT_API_URL,
    },
  );
}

export async function stopAgent(
  businessId: string,
  sessionId: string,
): Promise<VoiceSessionStatus> {
  return request<VoiceSessionStatus>("/agent/stop", {
    method: "POST",
    body: {
      business_id: businessId,
      session_id: sessionId,
    },
    baseUrl: VOICE_AGENT_API_URL,
  });
}
