/**
 * LiveKit voice client — connects to a LiveKit room where the Tendo agent lives.
 *
 * The agent handles STT, turn detection, TTS, and planner routing server-side.
 * This client just:
 * - Publishes the user's microphone audio
 * - Plays back the agent's audio
 * - Receives data messages (transcripts, responses, thinking status)
 */

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
} from 'livekit-client'

export type VoiceCallbacks = {
  onConnected: () => void
  onDisconnected: () => void
  onUserSpeakingChange: (speaking: boolean) => void
  onAgentSpeakingChange: (speaking: boolean) => void
  onMessage: (data: any) => void
  onThinking: (text: string) => void
  onTranscript: (text: string) => void
  onTurnComplete: () => void
  onError: (error: string) => void
}

export class LiveKitVoiceClient {
  private room: Room | null = null
  private localTrack: LocalAudioTrack | null = null
  private callbacks: VoiceCallbacks
  private audioElement: HTMLAudioElement | null = null

  constructor(callbacks: VoiceCallbacks) {
    this.callbacks = callbacks
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
    })

    this.room.on(RoomEvent.Connected, () => this.callbacks.onConnected())
    this.room.on(RoomEvent.Disconnected, () => this.callbacks.onDisconnected())

    // Agent publishes audio track — attach it for playback
    this.room.on(RoomEvent.TrackSubscribed, (track: RemoteTrack, _pub: RemoteTrackPublication, _participant: RemoteParticipant) => {
      if (track.kind === Track.Kind.Audio) {
        this.attachAudio(track)
        this.callbacks.onAgentSpeakingChange(true)
        track.on(TrackEvent.Ended, () => this.callbacks.onAgentSpeakingChange(false))
      }
    })

    this.room.on(RoomEvent.TrackUnsubscribed, (track: RemoteTrack) => {
      if (track.kind === Track.Kind.Audio) {
        this.detachAudio()
        this.callbacks.onAgentSpeakingChange(false)
      }
    })

    // Agent sends data messages (transcripts, responses, thinking)
    this.room.on(RoomEvent.DataReceived, (payload: Uint8Array) => {
      try {
        const text = new TextDecoder().decode(payload)
        const data = JSON.parse(text)

        switch (data.type) {
          case 'transcript':
            this.callbacks.onTranscript(data.data || '')
            break
          case 'message':
            this.callbacks.onMessage(data.data)
            break
          case 'thinking':
            this.callbacks.onThinking(data.data || '')
            break
          case 'turn_complete':
            this.callbacks.onTurnComplete()
            break
          case 'error':
            this.callbacks.onError(data.data || 'Unknown error')
            break
        }
      } catch {
        // ignore non-JSON
      }
    })

    // Track when the local user is speaking (via active speakers)
    this.room.on(RoomEvent.ActiveSpeakersChanged, (speakers) => {
      const local = this.room?.localParticipant
      if (!local) return
      const speaking = speakers.some(s => s.sid === local.sid)
      this.callbacks.onUserSpeakingChange(speaking)
    })

    await this.room.connect(url, token)
  }

  async startMic() {
    if (!this.room) throw new Error('Not connected')

    this.localTrack = await createLocalAudioTrack({
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
    })

    await this.room.localParticipant.publishTrack(this.localTrack)
  }

  stopMic() {
    if (this.localTrack) {
      this.room?.localParticipant.unpublishTrack(this.localTrack)
      this.localTrack.stop()
      this.localTrack = null
    }
  }

  sendText(text: string, metadata?: Record<string, string>) {
    if (!this.room || this.room.state !== ConnectionState.Connected) return false

    const payload = JSON.stringify({ type: 'text', data: text, ...metadata })
    this.room.localParticipant.publishData(
      new TextEncoder().encode(payload),
      { reliable: true }
    )
    return true
  }

  private attachAudio(track: RemoteTrack) {
    if (!this.audioElement) {
      this.audioElement = document.createElement('audio')
      this.audioElement.autoplay = true
      document.body.appendChild(this.audioElement)
    }
    track.attach(this.audioElement)
  }

  private detachAudio() {
    if (this.audioElement) {
      this.audioElement.srcObject = null
    }
  }

  isConnected(): boolean {
    return this.room?.state === ConnectionState.Connected
  }

  disconnect() {
    this.stopMic()
    if (this.audioElement) {
      this.audioElement.remove()
      this.audioElement = null
    }
    this.room?.disconnect()
    this.room = null
  }
}
