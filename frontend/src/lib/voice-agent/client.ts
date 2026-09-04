import {
  ConnectionState,
  createLocalAudioTrack,
  LocalAudioTrack,
  LogLevel,
  RemoteTrack,
  Room,
  RoomEvent,
  Track,
  TrackEvent,
  setLogLevel,
} from "livekit-client";

import type { VoiceClientCallbacks, VoiceDataMessage } from "./types";

setLogLevel(LogLevel.warn);

export class LiveKitVoiceClient {
  private room: Room | null = null;
  private localTrack: LocalAudioTrack | null = null;
  private audioElement: HTMLAudioElement | null = null;
  private callbacks: VoiceClientCallbacks;
  private agentReady = false;

  constructor(callbacks: VoiceClientCallbacks) {
    this.callbacks = callbacks;
  }

  async connect(url: string, token: string): Promise<void> {
    if (this.isConnected()) {
      return;
    }

    this.disconnect();

    const room = new Room({
      adaptiveStream: true,
      dynacast: true,
      audioCaptureDefaults: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });

    this.room = room;
    this.registerEvents(room);

    try {
      await room.connect(url, token);
      this.checkExistingAgent(room);
    } catch (error) {
      this.room = null;
      this.agentReady = false;
      throw error;
    }
  }

  async startMic(): Promise<void> {
    const room = this.requireRoom();

    if (this.localTrack) {
      return;
    }

    const track = await createLocalAudioTrack({
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
    });

    try {
      await room.localParticipant.publishTrack(track);
      this.localTrack = track;
    } catch (error) {
      track.stop();
      throw error;
    }
  }

  stopMic(): void {
    if (!this.localTrack || !this.room) {
      return;
    }

    try {
      this.room.localParticipant.unpublishTrack(this.localTrack);
    } finally {
      this.localTrack.stop();
      this.localTrack = null;
    }
  }

  sendPrompt(text: string): boolean {
    const room = this.room;

    if (!room || room.state !== ConnectionState.Connected) {
      return false;
    }

    const value = text.trim();

    if (!value) {
      return false;
    }

    const payload = JSON.stringify({
      type: "text",
      data: value,
    });

    room.localParticipant.publishData(new TextEncoder().encode(payload), {
      reliable: true,
    });

    return true;
  }

  isConnected(): boolean {
    return this.room?.state === ConnectionState.Connected;
  }

  isAgentReady(): boolean {
    return this.agentReady;
  }

  resetAgentReady(): void {
    this.agentReady = false;
  }

  disconnect(): void {
    this.stopMic();
    this.detachAudio();

    if (this.audioElement) {
      this.audioElement.remove();
      this.audioElement = null;
    }

    this.room?.disconnect();
    this.room = null;
    this.agentReady = false;
  }

  private registerEvents(room: Room): void {
    room.on(RoomEvent.Connected, () => {
      this.callbacks.onConnected();
    });

    room.on(RoomEvent.Disconnected, () => {
      this.agentReady = false;
      this.detachAudio();
      this.callbacks.onAgentSpeakingChange(false);
      this.callbacks.onDisconnected();
    });

    room.on(RoomEvent.ParticipantDisconnected, (participant) => {
      if (!this.isAgentParticipant(participant)) {
        return;
      }

      this.agentReady = false;
      this.detachAudio();
      this.callbacks.onAgentSpeakingChange(false);
      this.callbacks.onAgentLeft();
    });

    room.on(RoomEvent.TrackSubscribed, (track, publication, participant) => {
      if (!this.isAgentParticipant(participant)) {
        return;
      }

      if (track.kind !== Track.Kind.Audio) {
        return;
      }

      if (!this.agentReady) {
        this.agentReady = true;
        this.callbacks.onAgentReady();
      }

      this.attachAudio(track);

      track.on(TrackEvent.Ended, () => {
        this.callbacks.onAgentSpeakingChange(false);
      });
    });

    room.on(RoomEvent.TrackUnsubscribed, (track, publication, participant) => {
      if (!this.isAgentParticipant(participant)) {
        return;
      }

      if (track.kind !== Track.Kind.Audio) {
        return;
      }

      this.detachAudio();
      this.callbacks.onAgentSpeakingChange(false);
    });

    room.on(
      RoomEvent.ParticipantAttributesChanged,
      (changedAttributes, participant) => {
        if (!this.isAgentParticipant(participant)) {
          return;
        }

        const agentState = changedAttributes["lk.agent.state"];

        if (!agentState) {
          return;
        }

        if (agentState === "listening" && !this.agentReady) {
          this.agentReady = true;
          this.callbacks.onAgentReady();
        }

        if (agentState === "speaking") {
          this.callbacks.onAgentSpeakingChange(true);
          return;
        }

        if (agentState === "listening" || agentState === "thinking") {
          this.callbacks.onAgentSpeakingChange(false);
        }
      },
    );

    room.on(RoomEvent.DataReceived, (payload, participant) => {
      if (participant && !this.isAgentParticipant(participant)) {
        return;
      }

      this.handleData(payload);
    });

    room.on(RoomEvent.ActiveSpeakersChanged, (speakers) => {
      const localParticipant = room.localParticipant;

      const speaking = speakers.some(
        (participant) => participant.sid === localParticipant.sid,
      );

      this.callbacks.onUserSpeakingChange(speaking);
    });
  }

  private checkExistingAgent(room: Room): void {
    for (const participant of room.remoteParticipants.values()) {
      if (!this.isAgentParticipant(participant)) {
        continue;
      }

      const state = participant.attributes?.["lk.agent.state"];

      if (state === "listening") {
        this.agentReady = true;
        this.callbacks.onAgentReady();
        return;
      }

      if (state === "speaking") {
        if (!this.agentReady) {
          this.agentReady = true;
          this.callbacks.onAgentReady();
        }

        this.callbacks.onAgentSpeakingChange(true);
        return;
      }
    }
  }

  private handleData(payload: Uint8Array): void {
    try {
      const decoded = new TextDecoder().decode(payload);
      const data = JSON.parse(decoded) as VoiceDataMessage;

      switch (data.type) {
        case "transcript":
          this.callbacks.onTranscript(data.data);
          break;

        case "message":
          this.callbacks.onMessage(data.data);
          break;

        case "turn_complete":
          this.callbacks.onTurnComplete();
          break;

        case "error":
          this.callbacks.onError(data.data);
          break;
      }
    } catch {
      this.callbacks.onError("Failed to process voice data.");
    }
  }

  private attachAudio(track: RemoteTrack): void {
    if (!this.audioElement) {
      const audio: any = document.createElement("audio");

      audio.autoplay = true;
      audio.playsInline = true;

      document.body.appendChild(audio);

      this.audioElement = audio;
    }

    track.attach(this.audioElement);

    this.audioElement.play().catch(() => {});
  }

  private detachAudio(): void {
    if (!this.audioElement) {
      return;
    }

    this.audioElement.pause();
    this.audioElement.srcObject = null;
  }

  private isAgentParticipant(participant: {
    identity: string;
    attributes?: Record<string, string>;
  }): boolean {
    return (
      participant.attributes?.["lk.agent.name"] === "tendo-voice" ||
      participant.attributes?.["lk.agent.state"] !== undefined
    );
  }

  private requireRoom(): Room {
    if (!this.room) {
      throw new Error("Voice client is not connected.");
    }

    return this.room;
  }
}
