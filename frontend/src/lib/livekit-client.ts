import {
  Room,
  RoomEvent,
  Track,
  TrackEvent,
  RemoteTrack,
  RemoteTrackPublication,
  RemoteParticipant,
  LocalAudioTrack,
  createLocalAudioTrack,
  ConnectionState,
  LogLevel,
  setLogLevel,
} from "livekit-client";

// Suppress verbose LiveKit SDK logs in the browser console.
setLogLevel(LogLevel.warn);

export type VoiceCallbacks = {
  onConnected: () => void;
  onDisconnected: () => void;
  onAgentReady: () => void;
  onAgentLeft: () => void;
  onUserSpeakingChange: (speaking: boolean) => void;
  onAgentSpeakingChange: (speaking: boolean) => void;
  onMessage: (data: any) => void;
  onTranscript: (text: string) => void;
  onTurnComplete: () => void;
  onError: (error: string) => void;
};

export class LiveKitVoiceClient {
  private room: Room | null = null;
  private localTrack: LocalAudioTrack | null = null;
  private callbacks: VoiceCallbacks;
  private audioElement: HTMLAudioElement | null = null;
  private agentReady = false;

  constructor(callbacks: VoiceCallbacks) {
    this.callbacks = callbacks;
  }

  async connect(url: string, token: string) {
    this.room = new Room({
      adaptiveStream: true,
      dynacast: true,
      audioCaptureDefaults: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });

    this.room.on(RoomEvent.Connected, () => {
      this.callbacks.onConnected();
    });

    this.room.on(RoomEvent.Disconnected, () => {
      this.agentReady = false;
      this.detachAudio();
      this.callbacks.onAgentSpeakingChange(false);
      this.callbacks.onDisconnected();
    });

    this.room.on(
      RoomEvent.ParticipantDisconnected,
      (_participant: RemoteParticipant) => {
        this.agentReady = false;
        this.detachAudio();
        this.callbacks.onAgentSpeakingChange(false);
        this.callbacks.onAgentLeft();
      },
    );

    this.room.on(
      RoomEvent.TrackSubscribed,
      (
        track: RemoteTrack,
        _pub: RemoteTrackPublication,
        _participant: RemoteParticipant,
      ) => {
        if (track.kind === Track.Kind.Audio) {
          if (!this.agentReady) {
            this.agentReady = true;
            this.callbacks.onAgentReady();
          }
          this.attachAudio(track);
          track.on(TrackEvent.Ended, () =>
            this.callbacks.onAgentSpeakingChange(false),
          );
        }
      },
    );

    this.room.on(
      RoomEvent.ParticipantAttributesChanged,
      (
        changedAttributes: Record<string, string>,
        _participant: RemoteParticipant,
      ) => {
        const agentState = changedAttributes["lk.agent.state"];
        if (!agentState) return;

        if (agentState === "listening" && !this.agentReady) {
          this.agentReady = true;
          this.callbacks.onAgentReady();
        }

        if (agentState === "speaking") {
          this.callbacks.onAgentSpeakingChange(true);
        } else if (agentState === "listening" || agentState === "thinking") {
          this.callbacks.onAgentSpeakingChange(false);
        }
      },
    );

    for (const [, p] of this.room.remoteParticipants) {
      if (
        p.attributes?.["lk.agent.state"] === "listening" &&
        !this.agentReady
      ) {
        this.agentReady = true;
        this.callbacks.onAgentReady();
        break;
      }
    }

    this.room.on(RoomEvent.TrackUnsubscribed, (track: RemoteTrack) => {
      if (track.kind === Track.Kind.Audio) {
        this.detachAudio();
        this.callbacks.onAgentSpeakingChange(false);
      }
    });

    this.room.on(RoomEvent.DataReceived, (payload: Uint8Array) => {
      try {
        const text = new TextDecoder().decode(payload);
        const data = JSON.parse(text);

        switch (data.type) {
          case "transcript":
            this.callbacks.onTranscript(data.data || "");
            break;
          case "message":
            this.callbacks.onMessage(data.data);
            break;
          case "turn_complete":
            this.callbacks.onTurnComplete();
            break;
          case "error":
            this.callbacks.onError(data.data || "Unknown error");
            break;
        }
      } catch {}
    });

    this.room.on(RoomEvent.ActiveSpeakersChanged, (speakers) => {
      const local = this.room?.localParticipant;
      if (!local) return;
      const speaking = speakers.some((s) => s.sid === local.sid);
      this.callbacks.onUserSpeakingChange(speaking);
    });

    await this.room.connect(url, token);
  }

  async startMic() {
    if (!this.room) throw new Error("Not connected");

    // Always create a fresh track to avoid stale media stream issues
    if (this.localTrack) {
      try {
        this.room.localParticipant.unpublishTrack(this.localTrack);
      } catch {}
      this.localTrack.stop();
      this.localTrack = null;
    }

    this.localTrack = await createLocalAudioTrack({
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
    });

    await this.room.localParticipant.publishTrack(this.localTrack);
  }

  stopMic() {
    if (this.localTrack && this.room) {
      this.room.localParticipant.unpublishTrack(this.localTrack);
      this.localTrack.stop();
      this.localTrack = null;
    }
  }

  sendText(text: string, metadata?: Record<string, string>) {
    if (!this.room || this.room.state !== ConnectionState.Connected)
      return false;

    const payload = JSON.stringify({ type: "text", data: text, ...metadata });
    this.room.localParticipant.publishData(new TextEncoder().encode(payload), {
      reliable: true,
    });
    return true;
  }

  private attachAudio(track: RemoteTrack) {
    if (!this.audioElement) {
      this.audioElement = document.createElement("audio");
      this.audioElement.autoplay = true;
      (this.audioElement as any).playsInline = true;
      document.body.appendChild(this.audioElement);
    }
    track.attach(this.audioElement);
    this.audioElement.play().catch(() => {});
  }

  private detachAudio() {
    if (this.audioElement) {
      this.audioElement.pause();
      this.audioElement.srcObject = null;
    }
  }

  isConnected(): boolean {
    return this.room?.state === ConnectionState.Connected;
  }

  isAgentReady(): boolean {
    return this.agentReady;
  }

  resetAgentReady() {
    this.agentReady = false;
  }

  disconnect() {
    this.stopMic();
    if (this.audioElement) {
      this.audioElement.remove();
      this.audioElement = null;
    }
    this.room?.disconnect();
    this.room = null;
    this.agentReady = false;
  }
}
