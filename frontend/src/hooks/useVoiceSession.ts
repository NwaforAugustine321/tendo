import { useCallback, useRef, useState } from "react";
import { LiveKitVoiceClient } from "../lib/livekit-client";
import type { InputSpec } from "../components/containers/ConversationPage";
import { request } from "../lib/services/http";
import { connectSocket } from "../lib/ws";
import type { Socket } from "socket.io-client";
import { useBusinessStore } from "../store/business";
import { useAuthStore } from "../store/auth";

type SessionState =
  | "disconnected"
  | "connecting"
  | "warming"
  | "idle"
  | "listening"
  | "speaking"
  | "reconnecting"
  | "error";

export type AgentMessage = {
  id: string;
  response: string;
  msgType: "question" | "answer";
  questions?: InputSpec;
  extracted?: Record<string, string>;
};

type PreWarmData = {
  token: string;
  url: string;
  room: string;
};

const MAX_RECONNECT_ATTEMPTS = 3;
const RECONNECT_BASE_DELAY = 2000;

export function useVoiceSession() {
  const [state, setState] = useState<SessionState>("disconnected");
  const [lastMessage, setLastMessage] = useState<AgentMessage | null>(null);
  const [lastTranscript, setLastTranscript] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [thinkingText, setThinkingText] = useState("");
  const [thoughtText, setThoughtText] = useState("");
  const [micActive, setMicActive] = useState(false);
  const [userSpeaking, setUserSpeaking] = useState(false);
  const [agentSpeaking, setAgentSpeaking] = useState(false);
  const clientRef = useRef<LiveKitVoiceClient | null>(null);
  const socketRef = useRef<Socket | null>(null);
  const preWarmRef = useRef<PreWarmData | null>(null);
  const msgCounter = useRef(0);
  const connectParamsRef = useRef<{ sessionId?: string; businessId?: string }>(
    {},
  );
  const reconnectAttemptsRef = useRef(0);
  const disconnectingRef = useRef(false);

  const ensureSocket = useCallback((): Socket => {
    if (!socketRef.current) {
      const socket = connectSocket();
      socketRef.current = socket;

      socket.on("message", (data: any) => {
        const msg = typeof data === "string" ? JSON.parse(data) : data;
        if (msg.type === "message" && msg.data) {
          const { response, msg_type, questions, extracted } = msg.data;
          msgCounter.current++;
          setLastMessage({
            id: `msg-${msgCounter.current}`,
            response: response || "",
            msgType: msg_type || "answer",
            questions: questions || undefined,
            extracted: extracted || undefined,
          });
          setThinkingText("");
          setThoughtText("");
        } else if (msg.type === "thinking") {
          setThinkingText(msg.data || "");
        } else if (msg.type === "thought") {
          setThoughtText(msg.data || "");
        } else if (msg.type === "error") {
          setErrorMessage(msg.data || "Something went wrong");
        }
      });
    }
    return socketRef.current;
  }, []);

  const _redispatchAgent = useCallback(async () => {
    if (disconnectingRef.current) return;
    if (reconnectAttemptsRef.current >= MAX_RECONNECT_ATTEMPTS) {
      setErrorMessage("Agent connection lost. Please try again.");
      setState("error");
      return;
    }

    reconnectAttemptsRef.current++;
    const delay =
      RECONNECT_BASE_DELAY * Math.pow(2, reconnectAttemptsRef.current - 1);
    setState("reconnecting");

    await new Promise((resolve) => setTimeout(resolve, delay));

    if (disconnectingRef.current) return;

    const warmData = preWarmRef.current;
    const params = connectParamsRef.current;
    if (!warmData) return;

    try {
      await request("/voice/dispatch", {
        method: "POST",
        body: {
          room: warmData.room,
          business_id: params.businessId || "",
          session_id: params.sessionId || "",
        },
        silent: true,
      });
      clientRef.current?.resetAgentReady();
    } catch {
      _redispatchAgent();
    }
  }, []);

  const _createClient = useCallback(() => {
    return new LiveKitVoiceClient({
      onConnected: () => {},
      onAgentReady: () => {
        reconnectAttemptsRef.current = 0;
        if (micActive) {
          setState("listening");
        } else {
          setState("idle");
        }
      },
      onAgentLeft: () => {
        _redispatchAgent();
      },
      onDisconnected: () => {
        if (disconnectingRef.current) return;
        setState("disconnected");
        setMicActive(false);
        setAgentSpeaking(false);
        setUserSpeaking(false);
      },
      onUserSpeakingChange: (speaking) => setUserSpeaking(speaking),
      onAgentSpeakingChange: (speaking) => {
        setAgentSpeaking(speaking);
        if (speaking) setState("speaking");
        else if (micActive) setState("listening");
      },
      onMessage: (data) => {
        const { response, msg_type, questions, extracted } = data;
        msgCounter.current++;
        setLastMessage({
          id: `msg-${msgCounter.current}`,
          response: response || "",
          msgType: msg_type || "answer",
          questions: questions || undefined,
          extracted: extracted || undefined,
        });
        setThinkingText("");
        setThoughtText("");
      },
      onThinking: (text) => setThinkingText(text),
      onTranscript: (text) => setLastTranscript(text),
      onTurnComplete: () => {
        setAgentSpeaking(false);
        setState("listening");
      },
      onError: (err) => {
        setErrorMessage(err);
        setState("error");
      },
    });
  }, [_redispatchAgent]);

  const warmConnect = useCallback(
    async (params: { sessionId?: string; businessId?: string }) => {
      if (clientRef.current?.isConnected()) return;
      connectParamsRef.current = params;
      disconnectingRef.current = false;
      reconnectAttemptsRef.current = 0;
      setState("warming");

      const businessId =
        params.businessId ||
        useBusinessStore.getState().currentProfile?.id ||
        "";
      const userId = useAuthStore.getState().user?.user_id || "";
      if (!businessId || !userId) return;

      try {
        const warmData = await request<PreWarmData>("/voice/token", {
          method: "POST",
          body: { session_id: params.sessionId || "", business_id: businessId },
          silent: true,
        });
        preWarmRef.current = warmData;

        const client = _createClient();
        await client.connect(warmData.url, warmData.token);
        clientRef.current = client;
      } catch {
        setState("disconnected");
      }
    },
    [_createClient],
  );

  const connect = useCallback(
    async (params?: { sessionId?: string; businessId?: string }) => {
      setState("connecting");
      setErrorMessage("");
      disconnectingRef.current = false;

      const businessId =
        params?.businessId ||
        connectParamsRef.current.businessId ||
        useBusinessStore.getState().currentProfile?.id ||
        "";
      const userId = useAuthStore.getState().user?.user_id || "";

      if (!businessId || !userId) {
        setErrorMessage("Authentication or business profile required.");
        setState("error");
        return;
      }

      if (clientRef.current?.isConnected()) {
        try {
          await clientRef.current.startMic();
          setMicActive(true);
          setState("listening");
        } catch (err: any) {
          const msg =
            err?.name === "NotAllowedError"
              ? "Microphone permission denied."
              : "Could not access microphone.";
          setErrorMessage(msg);
          setState("error");
        }
        return;
      }

      let warmData = preWarmRef.current;
      if (!warmData) {
        try {
          warmData = await request<PreWarmData>("/voice/token", {
            method: "POST",
            body: {
              session_id: params?.sessionId || "",
              business_id: businessId,
            },
            silent: true,
          });
          preWarmRef.current = warmData;
        } catch {
          setErrorMessage("Failed to initialize voice session.");
          setState("error");
          return;
        }
      }

      if (!clientRef.current?.isConnected()) {
        try {
          const client = _createClient();
          await client.connect(warmData.url, warmData.token);
          clientRef.current = client;
        } catch {
          setErrorMessage("Voice connection failed.");
          setState("error");
          return;
        }
      }

      try {
        await clientRef.current!.startMic();
        setMicActive(true);
        setState("listening");
      } catch (err: any) {
        const msg =
          err?.name === "NotAllowedError"
            ? "Microphone permission denied."
            : "Could not access microphone.";
        setErrorMessage(msg);
        setState("error");
      }
    },
    [_createClient],
  );

  const disconnect = useCallback(async () => {
    disconnectingRef.current = true;
    const client = clientRef.current;
    const room = preWarmRef.current?.room;

    if (client) {
      client.stopMic();
      client.disconnect();
      clientRef.current = null;
    }

    setMicActive(false);
    setAgentSpeaking(false);
    setUserSpeaking(false);
    setState("disconnected");
    preWarmRef.current = null;

    if (room) {
      try {
        await request("/voice/stop", {
          method: "POST",
          body: { room },
          silent: true,
        });
      } catch {}
    }
  }, []);

  const startListening = useCallback(async () => {
    if (!clientRef.current?.isConnected()) return;
    try {
      await clientRef.current.startMic();
      setMicActive(true);
      setState("listening");
    } catch (err: any) {
      const msg =
        err?.name === "NotAllowedError"
          ? "Microphone permission denied."
          : "Could not access microphone.";
      setErrorMessage(msg);
      setState("error");
    }
  }, []);

  const stopListening = useCallback(() => {
    clientRef.current?.stopMic();
    setMicActive(false);
    setState("idle");
  }, []);

  const sendText = useCallback(
    (
      text: string,
      threadId?: string,
      businessId?: string,
      recordId?: string,
      sessionId?: string,
    ) => {
      const socket = ensureSocket();
      const storeBusinessId =
        businessId || useBusinessStore.getState().currentProfile?.id || "";
      socket.emit("message", {
        type: "text",
        data: text,
        business_id: storeBusinessId,
        session_id: sessionId || "",
        record_id: recordId || "",
      });
    },
    [ensureSocket],
  );

  return {
    state,
    lastMessage,
    lastTranscript,
    errorMessage,
    thinkingText,
    thoughtText,
    micActive,
    userSpeaking,
    agentSpeaking,
    isConnected:
      state === "listening" ||
      state === "speaking" ||
      state === "idle" ||
      state === "reconnecting",
    isListening: state === "listening",
    isSpeaking: state === "speaking",
    warmConnect,
    connect,
    disconnect,
    startListening,
    stopListening,
    sendText,
  };
}
